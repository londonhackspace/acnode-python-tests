#!/usr/bin/env python
#
# An acnode client in python
#

import socket, time

class Card:
  """
  unsigned int maintainer :1; // 1 if maintainer
  unsigned int uidlen     :1; // 1 if 7, otherwise 4
  unsigned int status     :1; // 1 if enabled
  unsigned int invalid    :1; // 0 if valid - by default the eeprom is set to 0xff
  unsigned int end        :1; // 1 if after the last valid uid 
  unsigned int            :3; // pad to a whole byte
    uint8_t uid[7];
    
  """
  def __init__(self, uid, maintainer, status):
    if uid < 2**32:
      assert(len("%08x" % (uid)) == (4*2))
    else:
     assert(len("%014x" % (uid)) == (7*2))
    self.uid = uid
    self.maintainer = maintainer
    self.status = status

  def __str__(self):
    if self.uid < 2**32:
      return "%08x" % (self.uid)
    else:
      return "%014x" % (self.uid)

class ACNode:
  def __init__(self, nodeid, servername, port, verbose=False):
    self.nodeid = nodeid
    self.servername = servername
    self.port = port
    self.status = 1
    self.verbose = verbose

    ret = self.networkCheckToolStatus()
    if ret != -1:
      self.status = ret

  def get_url(self, path):
    """
    The path arg includes the http method, e.g.:
    
    "GET /fish"
    "POST /wibble?foo=1"

    """
    result = -1

    socket.setdefaulttimeout(10.0)

    def get_constants(prefix):
      """Create a dictionary mapping socket module constants to their names."""
      return dict( (getattr(socket, n), n)
                    for n in dir(socket)
                    if n.startswith(prefix))
    families = get_constants('AF_')
    types = get_constants('SOCK_')
    protocols = get_constants('IPPROTO_')

    for res in socket.getaddrinfo(self.servername, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM):
      af, socktype, proto, canonname, sa = res
#      print families[af], types[socktype], protocols[proto]
      try:
        c = socket.socket(af, socktype, proto)
      except socket.error as msg:
        c = None
        continue
      try:
        c.connect(sa)
      except socket.error as msg:
        c.close()
        c = None
        continue
      break

#    print families[c.family], types[c.type], protocols[c.proto]

    if self.verbose:
      print
      print path
      print

    c.send(path)
    c.send(" HTTP/1.0\n")
    c.send("Host: ")
    c.send(self.servername+"\n");
    c.send("\n")

# timeout if not response after 10 secs
    c.setblocking(0)
    c.settimeout(10.0)

    first = False
    done = False
    while not done:
      try:
        data = c.recv(1024)
      except socket.error, e:
        if str(e) != "timed out":
          print e
        continue

      if len(data) == 0:
        done = True
        break

      lines = data.split("\r\n")
      try:
        result = int(lines[-1])
      except ValueError:
        pass

    c.close()

    return result

  def querycard(self, card):
    ret = self.get_url("GET /%d/card/%s" % (self.nodeid, card))

    if self.verbose:
      print "Got: %d" % (ret)

    if self.verbose:
      if ret == 1 or ret == 2:
        print "Access granted"
      elif ret == 0:
        print "Access denied"
      else:
        print "Network or Acserver error"
    
    return ret

  def networkCheckToolStatus(self):
    """
    https://wiki.london.hackspace.org.uk/view/Project:Tool_Access_Control/Solexious_Proposal#Check_tool_status
    """
    ret = self.get_url("GET /%d/status/" % (self.nodeid))

    if self.verbose:
      print "Status: %d" % (ret)
    
    return ret

  def setToolStatus(self, status, card):
    """
    https://wiki.london.hackspace.org.uk/view/Project:Tool_Access_Control/Solexious_Proposal#Report_tool_status
    """
    ret = self.get_url("POST /%ld/status/%d/by/%s" % (self.nodeid, status, card))

    if self.verbose:
      print "Got: %d" % (ret)
    
    return ret
    
  def addNewUser(self, user, maintainer):
    """
    https://wiki.london.hackspace.org.uk/view/Project:Tool_Access_Control/Solexious_Proposal#Add_card
    """
    if self.verbose:
      print "Adding card:"
    # /<nodeid>/grant-to-card/<trainee card uid>/by-card/<maintainer card uid>
    ret = self.get_url("POST /%ld/grant-to-card/%s/by-card/%s" % (self.nodeid, user, maintainer))

    if self.verbose:
      print "Got: %d" % (ret)
    
    return ret  

  def toolUseTime(self, card, time):
    """
    https://wiki.london.hackspace.org.uk/view/Project:Tool_Access_Control/Solexious_Proposal#Tool_usage_.28usage_time.29
    is the time here in ms or Seconds?
    """
    if self.verbose:
      print "Setting tool status:"
    # /[nodeID]/tooluse/time/for/[cardID]/[timeUsed]
    ret = self.get_url("POST /%ld/tooluse/time/for/%s/%d" % (self.nodeid, card, time))

    if self.verbose:
      print "Got: %d" % (ret)
    
    return ret

  def reportToolUse(self, card, status):
    """
    https://wiki.london.hackspace.org.uk/view/Project:Tool_Access_Control/Solexious_Proposal#Tool_usage_.28live.29
    """
    if self.verbose:
      print "Setting tool usage:"

    # /[nodeID]/tooluse/[status]/[cardID]

    ret = self.get_url("POST /%ld/tooluse/%d/%s" % (self.nodeid, status, card))

    if self.verbose:
      print "Got: %d" % (ret)

    return ret

if __name__ == "__main__":
  node = ACNode(1, "localhost", 1234)

  # card does not exist
  card = Card(0x12345678, False, True)
  print node.querycard(card)

  # card exists and is a user for this tool
  card = Card(0x22222222, False, True)
  print node.querycard(card)

  # card exists and is not a user for this tool
  card = Card(0x33333333, False, True)
  print node.querycard(card)
  
  # is a maintainer for this tool
  card = Card(0x00112233445566, False, True)
  print node.querycard(card)

  # is the same maintainer
  card = Card(0xaabbccdd, False, True)
  print node.querycard(card)

  # now the maintainer gives user id 3 permission to use the tool
  user = Card(0x33333333, False, True)
  maintainer = Card(0xaabbccdd, False, True)
  print node.addNewUser(user, maintainer)

  # and now they can use the tool
  card = Card(0x33333333, False, True)
  print node.querycard(card)

  # so they start using it  
  card = Card(0x33333333, False, True)
  print node.toolUse(1, card)

  # and stop after 5 seconds
  time.sleep(5)
  print node.toolUse(0, card)
  print node.toolUseTime(card, 5)
  
  # and then takes the tool offline
  print node.setToolStatus(0, card)

