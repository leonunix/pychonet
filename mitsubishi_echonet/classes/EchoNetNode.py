# from ..eojx import *
from ..epc  import EPC_CODE, EPC_SUPER
from ..functions import buildEchonetMsg, sendMessage, decodeEchonetMsg, getOpCode

"""
Superclass for Echonet instance objects.
"""

# Check status of Echonnet Instance
def _FF80(edt):
    ops_value = int.from_bytes(edt, 'big')
    return {'status': ('On' if ops_value == 0x30 else 'Off')}

def _009X(edt):
    payload = []
    if len(edt) < 17:
        for i in range (1, len(edt)):
            payload.append(edt[i])
        return payload

    for i in range (1, len(edt)):
        code = i-1
        binary = '{0:08b}'.format(edt[i])[::-1]
        for j in range (0, 8):
            if binary[j] == "1":
                EPC = (j+8) * 0x10 + code
                payload.append(EPC)
    return payload

# Check install location
def _0081(edt):
    # ops_value = int.from_bytes(edt, 'little')
    return {'install_location': None}
# Check standard version information
def _0082(edt):
    # ops_value = int.from_bytes(edt, 'little')
    return {'version_info': None}

# Check standard version information
def _008A(edt):
    ops_value = int.from_bytes(edt, 'big')
    return {'manufacturer': ops_value}


class EchoNetNode:

    """
    Constructs an object to represent an Echonet lite instance .

    :param eojgc: Echonet group code
    :param eojcc: Echonet class code
    :param instance: Instance ID
    :param netif: IP address of node
    """
    def __init__(self, eojgc, eojcc, instance = 0x1, netif="", polling = 10 ):
        self.netif = netif
        self.last_transaction_id = 0x1
        self.eojgc = eojgc
        self.eojcc = eojcc
        self.instance = instance
        self.available_functions = None
        self.status = False
        self.propertyMaps = self.getAllPropertyMaps()

    """
    getMessage is used to fire ECHONET request messages to get Node information
    Assumes one EPC is sent per message.

    :param tx_epc: EPC byte code for the request.
    :return: the deconstructed payload for the response

    """
    def getMessage(self, epc, pdc = 0x00):
        self.last_transaction_id += 1
        opc = [{'EPC': epc, 'PDC': pdc}]
        edt = getOpCode(self.netif, self.eojgc, self.eojcc, self.instance, opc, self.last_transaction_id )
        return edt


    """
    setMessage is used to fire ECHONET request messages to set Node information
    Assumes one OPC is sent per message.

    :param tx_epc: EPC byte code for the request.
    :param tx_edt: EDT data relevant to the request.
    :return: True if sucessful, false if request message failed
    """
    def setMessage(self, tx_epc, tx_edt):
        self.last_transaction_id += 1
        tx_payload = {
        'TID' : self.last_transaction_id,
        'DEOJGC': self.eojgc ,
        'DEOJCC': self.eojcc ,
        'DEOJIC': self.instance,
        'ESV' : SETC,
        'OPC' : [{'EPC': tx_epc, 'PDC': 0x01, 'EDT': tx_edt}]
        }
        message = buildEchonetMsg(tx_payload)
        data = sendMessage(message, self.netif);
        ## some index issue here sometimes
        try:
           rx = decodeEchonetMsg(data[0]['payload'])
        # if no data is returned ignore the IndexError and return false
        except IndexError:
           return False
        rx_epc = rx['OPC'][0]['EPC']
        rx_pdc = rx['OPC'][0]['PDC']
        if rx_epc == tx_epc and rx_pdc == 0x00:
            return True
        else:
            return False

    """
    getOperationalStatus returns the ON/OFF state of the node

    :return: status as a string.
    """
    def getOperationalStatus(self): # EPC 0x80
        raw_data = self.getMessage(0x80)[0]
        if raw_data['rx_epc'] == 0x80:
            return _FF80(raw_data['rx_edt'])


    """
    setOperationalStatus sets the ON/OFF state of the node

    :param status: True if On, False if Off.
    """
    def setOperationalStatus(self, status): # EPC 0x80
        return self.setMessage(0x80, 0x30 if status else 0x31)

    """
    On sets the node to ON.

    """
    def on (self): # EPC 0x80
        return self.setMessage(0x80, 0x30)

    """
    Off sets the node to OFF.

    """
    def off (self): # EPC 0x80
        return self.setMessage(0x80, 0x31)

    def fetchSetProperties (self): # EPC 0x9E
        if 0x9E in self.propertyMaps:
            return self.propertyMaps[0x9E]
        else:
            return {}

    def fetchGetProperties (self): # EPC 0x9F
        if 0x9F in self.propertyMaps:
            return self.propertyMaps[0x9F]
        else:
            return {}

    def getAllPropertyMaps(self):
        propertyMaps = {}
        property_map = getOpCode(self.netif, self.eojgc, self.eojcc, self.instance, [{'EPC':0x9F},{'EPC':0x9E}])
        for property in property_map:
            propertyMaps[property['rx_epc']] = {}
            for value in _009X(property['rx_edt']):
                    if value in EPC_CODE[self.eojgc][self.eojcc]:
                        propertyMaps[property['rx_epc']][EPC_CODE[self.eojgc][self.eojcc][value]] = value
                    elif value in EPC_SUPER:
                        propertyMaps[property['rx_epc']][EPC_SUPER[value]] = value
                    else:
                        print("code not found: " + hex(value) )
        return propertyMaps
