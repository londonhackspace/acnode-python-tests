#!/usr/bin/env python

import unittest, MySQLdb, time, urllib2, json, os, sys, subprocess
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
    if test_config.TESTMODE == "php":
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
      # and to test the api a bit better lets have a 2nd
      cur.execute("insert into tools (tool_id, name, status, status_message) VALUES (2, 'other test tool', 0, 'Out of action');")

      # and now an acnode for our tool
      cur.execute("insert into acnodes (acnode_id, unique_identifier, shared_secret, tool_id) VALUES (1, '1', '1', 1);")

      # make user 2 a user for this tool
      cur.execute("insert into permissions (tool_id, user_id, permission, added_on) VALUES (1, 2, 1, NOW());")
    
      # make user 1 a maintainer for this tool
      cur.execute("insert into permissions (tool_id, user_id, permission, added_on) VALUES (1, 1, 2, NOW());")

      # make the android tag a user
      cur.execute("insert into permissions (tool_id, user_id, permission, added_on) VALUES (1, 8, 1, NOW());")

      # make the temp card a maintainer
      cur.execute("insert into permissions (tool_id, user_id, permission, added_on) VALUES (1, 5, 2, NOW());")

      # make user 4 a maintainer
      cur.execute("insert into permissions (tool_id, user_id, permission, added_on) VALUES (1, 4, 2, NOW());")

      db.commit()
      db.close()
    elif test_config.TESTMODE == "django":
      os.environ['DJANGO_SETTINGS_MODULE'] = 'acserver.settings'
      import django
      if os.path.exists(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.path.sep + "acserver-django" ):
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.path.sep + "acserver-django")
      else:
        if test_config.ACNODE_ACSERVER_DJANGO:
          sys.path.append(test_config.ACNODE_ACSERVER_DJANGO)
        else:
          raise RunTimeException("you need to put acserver-django on your python path somehow, bodge this here.")
      from server.models import Tool, Card, User, Permissions
      from django.core.exceptions import ObjectDoesNotExist

      django.setup()
      try:
        t = Tool.objects.get(id=1)
        t.delete()
        t = None
      except ObjectDoesNotExist, e:
        pass

      try:
        t = Tool.objects.get(id=2)
        t.delete()
        t = None
      except ObjectDoesNotExist, e:
        pass

      t = Tool(id=1, name='test_tool', status=1, status_message='working ok')
      t.save()

      t = Tool(id=2, name='other test tool', status=0, status_message='Out of action')
      t.save()

      # clean permissions first
      ps = Permissions.objects.all()
      for p in ps:
        p.delete()
        p = None

      # user 2 is a user
      p = Permissions(user=User.objects.get(pk=2), permission=1, tool=Tool.objects.get(pk=1), addedby=User.objects.get(pk=1))
      p.save()
      # user 1 is a maintainer
      p = Permissions(user=User.objects.get(pk=1), permission=2, tool=Tool.objects.get(pk=1), addedby=User.objects.get(pk=1))
      p.save()
      # make the android tag a user
      p = Permissions(user=User.objects.get(pk=8), permission=1, tool=Tool.objects.get(pk=1), addedby=User.objects.get(pk=1))
      p.save()
      # make the temp card a maintainer
      p = Permissions(user=User.objects.get(pk=5), permission=2, tool=Tool.objects.get(pk=1), addedby=User.objects.get(pk=1))
      p.save()
      # make user 4 a maintainer
      p = Permissions(user=User.objects.get(pk=4), permission=2, tool=Tool.objects.get(pk=1), addedby=User.objects.get(pk=1))
      p.save()

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
  
  def test_user_and_not_subscribed(self):
    # card exists and is a user for this tool, but is not subscribed
    self.failUnless(self.node.querycard(self.user4) == -1)

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

  def test_noperms_user_adds_a_card(self):
    # known user with no perms for this tool tries to add a card
    self.failUnless(self.node.addNewUser(self.user3, self.user3) == 0)

  def test_unsubscribed_maintainer_adds_a_card(self):
    self.failUnless(self.node.addNewUser(self.user3, self.user4) == 0)

  def test_user_already_has_perms(self):
    self.failUnless(self.node.addNewUser(self.user2, self.user1a) == 1)

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

  def test_non_maintainer_set_online(self):
    # take the tool offline
    self.failUnless(self.node.setToolStatus(0, self.user2) == 1)
    # non maintainer putting online
    self.failUnless(self.node.setToolStatus(1, self.user2) == 0)

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

  def test_get_tools_summary_for_user_toolstuff(self):
    # get_tools_summary_for_user
    # "/api/get_tools_summary_for_user/%d" % (2)
    req = urllib2.Request("http://%s:%d/api/get_tools_summary_for_user/%d" %
      (self.node.servername, self.node.port, 1),
      headers={'API-KEY': 'KEY GOES HERE'})
    response = urllib2.urlopen(req)
    ret = json.loads(response.read())
    self.failUnless(ret[0]['permission'] == 'maintainer')
    self.failUnless(ret[0]['status'] == 'Operational')
    self.failUnless(ret[0]['status_message'] == 'working ok')
    self.failUnless(ret[0]['name'] == 'test_tool')
    self.failUnless(ret[0]['in_use'] == 'no')

  def test_get_tools_summary_for_user_does_not_exist(self):
    # get_tools_summary_for_user for user who does not exist
    # "/api/get_tools_summary_for_user/%d" % (2)
    req = urllib2.Request("http://%s:%d/api/get_tools_summary_for_user/%d" %
      (self.node.servername, self.node.port, 42),
      headers={'API-KEY': 'KEY GOES HERE'})
    response = urllib2.urlopen(req)
    ret = json.loads(response.read())
    self.failUnless(ret[0]['permission'] == 'un-authorised')
    self.failUnless(ret[1]['permission'] == 'un-authorised')

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
      self.failUnless(str(e).startswith('HTTP Error 401'))

class DbUpdateTests(unittest.TestCase):
  # assumes 0_carddb.json is already loaded

  user3  = Card(0x33333333, False, True)
  user3a = Card(0x33333300, False, True)
  user4  = Card(0x44444444, False, True)

  djpath = None

  def setUp(self):
    if test_config.TESTMODE == "php":
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

      # make user 4 a user
      cur.execute("insert into permissions (tool_id, user_id, permission, added_on) VALUES (1, 3, 1, NOW());")
      db.commit()
      db.close()
    elif test_config.TESTMODE == "django":
      os.environ['DJANGO_SETTINGS_MODULE'] = 'acserver.settings'
      import django
      djpath = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.path.sep + "acserver-django"
      if os.path.exists(djpath):
        sys.path.append(djpath)
        self.djpath = djpath
      else:
        if test_config.ACNODE_ACSERVER_DJANGO:
          sys.path.append(test_config.ACNODE_ACSERVER_DJANGO)
          self.djpath = test_config.ACNODE_ACSERVER_DJANGO
        else:
          raise RunTimeException("you need to put acserver-django on your python path somehow, bodge this here.")
      from server.models import Tool, Card, User, Permissions
      from django.core.exceptions import ObjectDoesNotExist

      django.setup()
      try:
        t = Tool.objects.get(id=1)
        t.delete()
        t = None
      except ObjectDoesNotExist, e:
        pass

      t = Tool(id=1, name='test_tool', status=1, status_message='working ok')
      t.save()
      # clean permissions first
      ps = Permissions.objects.all()
      for p in ps:
        p.delete()
        p = None
      # make user 3 a user
      p = Permissions(user=User.objects.get(pk=3), permission=1, tool=Tool.objects.get(pk=1), addedby=User.objects.get(pk=1))
      p.save()

    self.node = ACNode(1, test_config.ACNODE_ACSERVER_HOST, test_config.ACNODE_ACSERVER_PORT)

  def update_carddb(self, file):
    if test_config.TESTMODE == "php":
      raise RunTimeError("Please implement php mode")
    elif test_config.TESTMODE == "django":
      update = [self.djpath + os.path.sep + "manage.py", "updatecarddb", file]
      subprocess.call(update)

  def test_start(self):
    # card exists and is a user for this tool
    self.failUnless(self.node.querycard(self.user3) == 1)
    # this card does not exist yet
    self.failUnless(self.node.querycard(self.user3a) == -1)

  def test_cardb_updates(self):
    # this card does not exist yet
    self.failUnless(self.node.querycard(self.user3a) == -1)
    self.update_carddb("1_card_added_carddb.json")
    # should exist now
    self.failUnless(self.node.querycard(self.user3a) == 1)
    self.update_carddb("2_card_removed_carddb.json")
    # and now it's gone
    self.failUnless(self.node.querycard(self.user3a) == -1)
    # user3 should be ok
    self.failUnless(self.node.querycard(self.user3) == 1)
    # un subscribe them
    self.update_carddb("3_user_unsubscribed_carddb.json")
    # and now they don't work
    self.failUnless(self.node.querycard(self.user3) == -1)
    # re-subscribe them
    self.update_carddb("4_user_subscribed_carddb.json")
    # and now they should work
    self.failUnless(self.node.querycard(self.user3) == 1)


class SecretTests(unittest.TestCase):
  # assumes 0_carddb.json is already loaded

  user3  = Card(0x33333333, False, True)
  user3a = Card(0x33333300, False, True)
  user4  = Card(0x44444444, False, True)

  djpath = None

  def setUp(self):
    if test_config.TESTMODE == "php":
      raise RunTimeError("only the django server supports secret key thingys")
    elif test_config.TESTMODE == "django":
      os.environ['DJANGO_SETTINGS_MODULE'] = 'acserver.settings'
      import django
      djpath = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.path.sep + "acserver-django"
      if os.path.exists(djpath):
        sys.path.append(djpath)
        self.djpath = djpath
      else:
        if test_config.ACNODE_ACSERVER_DJANGO:
          sys.path.append(test_config.ACNODE_ACSERVER_DJANGO)
          self.djpath = test_config.ACNODE_ACSERVER_DJANGO
        else:
          raise RunTimeException("you need to put acserver-django on your python path somehow, bodge this here.")
      from server.models import Tool, Card, User, Permissions
      from django.core.exceptions import ObjectDoesNotExist

      django.setup()
      try:
        t = Tool.objects.get(id=1)
        t.delete()
        t = None
        t = Tool.objects.get(id=2)
        t.delete()
        t = None
      except ObjectDoesNotExist, e:
        pass

      t = Tool(id=1, name='test_tool', status=1, status_message='working ok')
      t.save()
      t = Tool(id=2, name='test_tool_with_secret', status=1, status_message='working ok', secret='12345678')
      t.save()
      # clean permissions first
      ps = Permissions.objects.all()
      for p in ps:
        p.delete()
        p = None
      # make user 3 a user for tool 1
      p = Permissions(user=User.objects.get(pk=3), permission=1, tool=Tool.objects.get(pk=1), addedby=User.objects.get(pk=1))
      p.save()
      # and 2
      p = Permissions(user=User.objects.get(pk=3), permission=1, tool=Tool.objects.get(pk=2), addedby=User.objects.get(pk=1))
      p.save()

    self.node = ACNode(1, test_config.ACNODE_ACSERVER_HOST, test_config.ACNODE_ACSERVER_PORT)
    self.node_one_with_secret = ACNode(1, test_config.ACNODE_ACSERVER_HOST, test_config.ACNODE_ACSERVER_PORT, secret='abcdefgh')
    self.secret_node = ACNode(2, test_config.ACNODE_ACSERVER_HOST, test_config.ACNODE_ACSERVER_PORT, secret='12345678')
    self.missing_secret_node = ACNode(2, test_config.ACNODE_ACSERVER_HOST, test_config.ACNODE_ACSERVER_PORT)
    self.wrong_secret_node = ACNode(2, test_config.ACNODE_ACSERVER_HOST, test_config.ACNODE_ACSERVER_PORT, secret='xxxxxxxx')

  def test_start(self):
    # card exists and is a user for this tool
    self.failUnless(self.node.querycard(self.user3) == 1)
    # this card does not exist yet
    self.failUnless(self.node.querycard(self.user3a) == -1)

    # card exists and is a user for this tool
    self.failUnless(self.secret_node.querycard(self.user3) == 1)
    # this card does not exist yet
    self.failUnless(self.secret_node.querycard(self.user3a) == -1)

  def test_node_missing_secret(self):
    # card exists and is a user for this tool
    # but the secret is missing now so it will fail
    self.failUnless(self.missing_secret_node.querycard(self.user3) == 0)

  def test_Server_missing_secret(self):
    # we are sending an unexpected secret. the server should accept it (and log it)
    self.failUnless(self.node_one_with_secret.querycard(self.user3) == 1)

  def test_wrong_secret(self):
    # we are sending the wrong secret, so should be refused
    self.failUnless(self.wrong_secret_node.querycard(self.user3) == 0)

if __name__ == '__main__':
  unittest.main()
#  suite = unittest.TestLoader().loadTestsFromTestCase(AcnodeTests)
#  unittest.TextTestRunner(verbosity=2).run(suite)
