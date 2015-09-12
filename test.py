#!/usr/bin/env python

import unittest, MySQLdb, time, urllib2, json
from acnode import ACNode, Card
import test_config

class AcnodeTests(unittest.TestCase):
  # user 1 has 2 cards, and is a maintainer
  user1a = Card(0x00112233445566, False, True)
  user1b = Card(0xaabbccdd, False, True)

  # a user
  user2 = Card(0x22222222, False, True)

  # subscribed, but not a user
  user3 = Card(0x33333333, False, True)

  # exists, but not is not subscribed
  user4 = Card(0x44444444, False, True)

  user_does_not_exist = Card(0x12345678, False, True)

  def setUp(self):
    """
    import users and cards into the db:
    
    sudo cp carddb.json /run/carddb.php
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
    db = MySQLdb.connect(host=test_config.MYSQL_HOST,
                         user=test_config.MYSQL_USER,
                         passwd=test_config.MYSQL_PASS,
                         db=test_config.MYSQL_DB)
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

    self.node = ACNode(1, test_config.ACNODE_ACSERVER_HOST, test_config.ACNODE_ACSERVER_PORT)

  def test_online(self):
    # should be online now
    self.failUnless(self.node.networkCheckToolStatus() == 1)

  def test_online_tool_does_not_exist(self):
    # test with an unknown tool_id
    node = ACNode(123, test_config.ACNODE_ACSERVER_HOST, test_config.ACNODE_ACSERVER_PORT)
    self.failUnless(node.networkCheckToolStatus() == -1)

  def test_card_not_exists(self):
    self.failUnless(self.node.querycard(self.user_does_not_exist) == -1)

  def test_user(self):
    # card exists and is a user for this tool
    self.failUnless(self.node.querycard(self.user2) == 1)

  def test_user_exists_and_not_user(self):
    # card exists and is not a user for this tool
    self.failUnless(self.node.querycard(self.user3) == 0)
  
  def test_maintainer(self):
    # is a maintainer for this tool
    self.failUnless(self.node.querycard(self.user1a) == 2)

  def test_maintainer_multi_cards(self):
    # is the same maintainer
    self.failUnless(self.node.querycard(self.user1b) == 2)

  def test_adduser(self):
    # now the maintainer gives user id 3 permission to use the tool
    self.failUnless(self.node.addNewUser(self.user3, self.user1a) == 1)
    # and now they can use the tool
    self.failUnless(self.node.querycard(self.user3) == 1)

  def test_add_unknown(self):
    # maintainer add unknown card
    self.failUnless(self.node.addNewUser(self.user_does_not_exist, self.user1a) == 0)

  def test_add_unsubscribed(self):
    # maintainer adds known, unsubscribed card
    self.failUnless(self.node.addNewUser(self.user4, self.user1a) == 0)

  def test_non_maintainer_add(self):
    # know user tries to add a card
    self.failUnless(self.node.addNewUser(self.user3, self.user2) == 0)

  def test_unknown_user_adds_a_card(self):
    # unknown user tries to add a card
    self.failUnless(self.node.addNewUser(self.user3, self.user_does_not_exist) == 0)

  def test_using_acnode(self):
    self.failUnless(self.node.reportToolUse(self.user2, 1) == 1)
    # and stop after 5 seconds
    time.sleep(5)
    self.failUnless(self.node.toolUseTime(self.user2, 5) == 1)
    self.failUnless(self.node.reportToolUse(self.user2, 0) == 1)

  def test_set_offline(self):
    # take the tool offline
    self.failUnless(self.node.setToolStatus(0, self.user2) == 1)
  
  def test_unknown_set_offline(self):
    # only known users can take a tool offline
    self.failUnless(self.node.setToolStatus(0, self.user_does_not_exist) == 0)

  def test_not_user_set_offline(self):
    # known but not a user
    self.failUnless(self.node.setToolStatus(0, self.user3) == 1)

  def test_new_user_put_offline(self):
    # let them use the tool
    self.failUnless(self.node.addNewUser(self.user3, self.user1a) == 1)
    # check that they can use it
    self.failUnless(self.node.querycard(self.user3) == 1)
    # and take the tool out of service
    self.failUnless(self.node.setToolStatus(0, self.user3) == 1)
    # and we should be out of service now
    self.failUnless(self.node.networkCheckToolStatus() == 0)

  def test_error(self):
    card = Card(0x00000000, False, True)
    # acnode does not exist
    node = ACNode(42, test_config.ACNODE_ACSERVER_HOST, test_config.ACNODE_ACSERVER_PORT)
    # this test fails atm, it's not a big deal tho.
    self.failUnless(node.querycard(card) == -1)

  def test_toolisinuse(self):
    # not called by the acnodes, but by things monitoring them.
    # start using the tool
    self.failUnless(self.node.reportToolUse(self.user2, 1) == 1)
    response = urllib2.urlopen(("http://%s:%d/%d/is_tool_in_use" % (self.node.servername, self.node.port, self.node.nodeid)))
    self.failUnless(response.read() == "yes")

    # if the tool starts and stops in the same second then this fails
    time.sleep(1)

    # and stop
    self.failUnless(self.node.reportToolUse(self.user2, 0) == 1)

    response = urllib2.urlopen("http://%s:%d/%d/is_tool_in_use" % (self.node.servername, self.node.port, self.node.nodeid))
    ret = response.read()
    # this fails if the tool is used for less than a second actual bug?
    self.failUnless(ret == "no")

  # apikey tests
  # API-KEY: 'KEY GOES HERE'
  def test_get_tools_summary_for_user(self):
    # get_tools_summary_for_user
    # "/api/get_tools_summary_for_user/%d" % (2)
    req = urllib2.Request("http://%s:%d/api/get_tools_summary_for_user/%d" %
      (self.node.servername, self.node.port, 1),
      headers={'API-KEY': 'KEY GOES HERE'})
    response = urllib2.urlopen(req)
    ret = json.loads(response.read())
    self.failUnless(ret[0]['permission'] == 'maintainer')

  def test_get_tools_summary_for_user_does_not_exist(self):
    # get_tools_summary_for_user for user who does not exist
    # "/api/get_tools_summary_for_user/%d" % (2)
    req = urllib2.Request("http://%s:%d/api/get_tools_summary_for_user/%d" %
      (self.node.servername, self.node.port, 42),
      headers={'API-KEY': 'KEY GOES HERE'})
    response = urllib2.urlopen(req)
    ret = json.loads(response.read())
    self.failUnless(ret[0]['permission'] == 'un-authorised')

  def test_get_tools_summary_for_user_adding_user(self):
    # get_tools_summary_for_user for user who is not authorised, and
    # then add them, then test again
    # "/api/get_tools_summary_for_user/%d" % (2)
    req = urllib2.Request("http://%s:%d/api/get_tools_summary_for_user/%d" %
      (self.node.servername, self.node.port, 3),
      headers={'API-KEY': 'KEY GOES HERE'})
    response = urllib2.urlopen(req)
    ret = json.loads(response.read())
    self.failUnless(ret[0]['permission'] == 'un-authorised')

    # add user 3 as a user
    self.failUnless(self.node.addNewUser(self.user3, self.user1a) == 1)
    # and now they can use the tool
    self.failUnless(self.node.querycard(self.user3) == 1)

    # now check they can use the tool
    req = urllib2.Request("http://%s:%d/api/get_tools_summary_for_user/%d" %
      (self.node.servername, self.node.port, 3),
      headers={'API-KEY': 'KEY GOES HERE'})
    response = urllib2.urlopen(req)
    ret = json.loads(response.read())
    self.failUnless(ret[0]['permission'] == 'user')

  def test_get_tools_summary_for_user_wrong_api_key(self):
    # get_tools_summary_for_user with wrong api key
    # "/api/get_tools_summary_for_user/%d" % (2)
    req = urllib2.Request("http://%s:%d/api/get_tools_summary_for_user/%d" %
      (self.node.servername, self.node.port, 42),
      headers={'API-KEY': 'udlrabss'})
    try:
      response = urllib2.urlopen(req)
      ret = json.loads(response.read())
      print ret
      self.failUnless(ret == "something")
    except urllib2.HTTPError, e:
      self.failUnless(str(e) == 'HTTP Error 401: Forbidden')

  def test_whois_known_card(self):
    # whois for a known card returns user id, to be announced via irc
    req = urllib2.Request("http://%s:%d/api/whois/%s" % (self.node.servername, self.node.port, self.user2))
    try:
      response = urllib2.urlopen(req)
      lines = response.read().split("\r\n")
      self.failUnless(lines[0] == "test2")
      self.failUnless(lines[1] == "22222222")
    except urllib2.HTTPError, e:
      self.failUnless(str(e) == 'HTTP Error 401: Forbidden')

if __name__ == '__main__':
  unittest.main()
#  suite = unittest.TestLoader().loadTestsFromTestCase(AcnodeTests)
#  unittest.TextTestRunner(verbosity=2).run(suite)


