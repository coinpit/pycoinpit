import requests
import binascii
import pybitcointools
import pyelliptic
import time
import hmac
import hashlib
import orders

class Client(object):

    def __init__(self, key=None):
        self.testnet_base_url = "https://live.coinpit.me/api/v1"
        self.livenet_base_url = "https://live.coinpit.io/api/v1"
        self.private_key = key
        self.user_pub_key = None
        self.server_pub_key = None
        self.shared_secret = None
        if(self.private_key == None):
            return
        if (self.private_key[0] == 'K' or self.private_key[0] == 'L'):
            self.base_url = self.livenet_base_url
            self.network_code = 0
        else:
            self.base_url = self.testnet_base_url
            self.network_code = 111
        self.user_pub_key = pybitcointools.privtopub(self.private_key)
        self.user_id = pybitcointools.pubtoaddr(self.user_pub_key, self.network_code)

    def get_server_pubkey(self):
        if self.server_pub_key != None:
            return
        if (self.private_key == None):
            raise ValueError('Private key needed for protected endpoints')
        auth_info = self.server_call("/auth/" + self.user_pub_key)
        return auth_info['serverPublicKey']


    def connect(self):
        self.server_pub_key = self.get_server_pubkey()
        self.get_shared_secret()

    def get_shared_secret(self):
        pub_key_bytes        = binascii.unhexlify(self.server_pub_key)
        uncompressed_user_key   = binascii.unhexlify(pybitcointools.decompress(self.user_pub_key))
        uncompressed_server_key = binascii.unhexlify(pybitcointools.decompress(self.server_pub_key))
        user_priv_key_bin       = binascii.unhexlify(pybitcointools.encode_privkey(self.private_key, 'hex', self.network_code))
        self.user               = pyelliptic.ECC(privkey=user_priv_key_bin, pubkey=uncompressed_user_key, curve='secp256k1')
        self.shared_secret      = self.user.get_ecdh_key(uncompressed_server_key)

    def get_headers(self, method, uri, body=None):
        self.connect()
        rest_url = uri
        # Use unix time as nonce
        nonce = str(long(time.time() * 1000))
        request_string = '{"method":"' + method + '","uri":"' + rest_url  + ('",' if(body == None) else '","body":' + body + ',') + '"nonce":' + nonce + '}'
        mac = hmac.new(self.shared_secret, request_string,    hashlib.sha256)
        sig = mac.hexdigest()
        headers = {
            'Authorization': 'HMAC ' + self.user_id + ':' + sig,
            'Nonce': nonce,
            'Accept': 'application/json'
        }
        return headers

    def info(self):
        return self.server_call("/all/info")

    def get_account(self):
        return self.auth_call("GET", "/account")

    def patch_orders(self, patch_spec):
        orders.patch(self, patch_spec)

    def cancel_orders(self, cancel_spec):
        orders.cancel(self, cancel_spec)

    def cancel_all_orders(self):
        orders.cancel_all(self)

    def update_orders(self, update_spec):
        orders.update(self, update_spec)

    def create_orders(self, create_spec):
        orders.create(self, create_spec)

    def get_open_orders(self, get_open_spec):
        orders.get_open(self, get_open_spec)

    def get_closed_orders(self, get_closed_spec):
        orders.get_closed(self, get_closed_spec)

    def get_cancelled_orders(self, get_cancelled_spec):
        orders.get_cancelled(self, get_cancelled_spec)

    def server_call(self, url, headers={'Accept': 'application/json'}):
        try:
            return requests.get(self.base_url + url, headers=headers).json()
        except Exception as err:
            print "Error calling {} \n {}".format(self.base_url + url, err)

    def auth_call(self, method, url, body=None):
        try:
            headers = self.get_headers(method, url, body)
            print "###########{}".format(headers)
            return requests.get(self.base_url + url, headers=headers).json()
        except Exception as err:
            print "Error on Auth call {} \n {}".format(self.base_url + url, err)
