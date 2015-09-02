#!/usr/bin/env python

import unittest, MySQLdb, time
from acnode import ACNode, Card

class AcnodeTests(unittest.TestCase):

  def setUp(self):
    """
    import users and cards into the db:
    
    sudo cp carddb.json to /run/carddb.php
    cd /var/www/acserver ; php index.php update_from_carddb
    
    # add a tool
    insert into tools (tool_id, name, status, status_message) VALUES (1, 'test_tool', 1, 'working ok');

    # and an acnode:
    insert into acnodes (acnode_id, unique_identifier, shared_secret, tool_id) VALUES (1, '1', '1', 1);
    
    # make user 2 a user for this tool
    insert into permissions (tool_id, user_id, permission) VALUES (1, 2, 1);
    
    # make user 1 a maintainer for this tool
    insert into permissions (tool_id, user_id, permission) VALUES (1, 1, 2);
    
    """
    db = MySQLdb.connect(host="localhost",
                         user="acserver",
                         passwd="acserverzz",
                         db="acserver")
    cur = db.cursor()
    cur.execute("DELETE FROM permissions;")
    cur.execute("DELETE FROM acnodes;")
    cur.execute("DELETE FROM toolusage;")    
    cur.execute("DELETE FROM tools;")

    # we need a tool to test with
    cur.execute("insert into tools (tool_id, name, status, status_message) VALUES (1, 'test_tool', 1, 'working ok');")

    # and now an acnode for our tool
    cur.execute("insert into acnodes (acnode_id, unique_identifier, shared_secret, tool_id) VALUES (1, '1', '1', 1);")

    # make user 2 a user for this tool
    cur.execute("insert into permissions (tool_id, user_id, permission, added_on) VALUES (1, 2, 1, NOW());")
    
    # make user 1 a maintainer for this tool
    cur.execute("insert into permissions (tool_id, user_id, permission, added_on) VALUES (1, 1, 2, NOW());")
    
    db.commit()
    db.close()

    self.node = ACNode(1, "localhost", 1234)

  def test_online(self):
    # should be online now
    self.failUnless(self.node.networkCheckToolStatus() == 1)

  def test_card_not_exists(self):
    card = Card(0x12345678, False, True)
    self.failUnless(self.node.querycard(card) == 0)

  def test_user(self):
    # card exists and is a user for this tool
    card = Card(0x22222222, False, True)
    self.failUnless(self.node.querycard(card) == 1)

  def test_user_exists_and_not_user(self):
    # card exists and is not a user for this tool
    card = Card(0x33333333, False, True)
    self.failUnless(self.node.querycard(card) == 0)
  
  def test_maintainer(self):
    # is a maintainer for this tool
    card = Card(0x00112233445566, False, True)
    self.failUnless(self.node.querycard(card) == 2)

  def test_maintainer_multi_cards(self):
    # is the same maintainer
    card = Card(0xaabbccdd, False, True)
    self.failUnless(self.node.querycard(card) == 2)

  def test_adduser(self):
    # now the maintainer gives user id 3 permission to use the tool
    user = Card(0x33333333, False, True)
    maintainer = Card(0xaabbccdd, False, True)
    assert(self.node.addNewUser(user, maintainer) == 1)
    # and now they can use the tool
    self.failUnless(self.node.querycard(user) == 1)

  def test_using_acnode(self):
    # so they start using it  
    card = Card(0x33333333, False, True)
    assert(self.node.reportToolUse(card, 1) == 1)
    # and stop after 5 seconds
    time.sleep(5)
    ret = self.node.toolUseTime(card, 5)
    self.node.reportToolUse(card, 0)
    self.failUnless(ret == 1)

  def test_set_offline(self):
    card = Card(0x33333333, False, True)
    # and then takes the tool offline
    self.failUnless(self.node.setToolStatus(0, card) == 1)
  
  def test_now_offline(self):
    # should be offline now
    user = Card(0x33333333, False, True)
    maintainer = Card(0xaabbccdd, False, True)
    assert(self.node.addNewUser(user, maintainer) == 1)
    # and now they can use the tool
    assert(self.node.querycard(user) == 1)
    # take the tool out of service
    assert(self.node.setToolStatus(0, user) == 1)
    # and we should be out of service now
    self.failUnless(self.node.networkCheckToolStatus() == 0)

  def test_error(self):
    card = Card(0x00000000, False, True)
    # acnode does not exist
    node = ACNode(42, "localhost", 1234)
    # this test fails atm, it's not a big deal tho.
    self.failUnless(node.querycard(card) == -1)

if __name__ == '__main__':
  suite = unittest.TestLoader().loadTestsFromTestCase(AcnodeTests)
  unittest.TextTestRunner(verbosity=2).run(suite)

#  unittest.main()
