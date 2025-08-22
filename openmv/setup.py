import sys
import os
from rsa.key import newkeys

def setup_rsa(nodeaddr):
    print("\nGeneration RSA Keys for node {nodeaddr}")
    (pubkey, privkey) = newkeys(1024)
    fname = f"{nodeaddr}.pub"
    f = open(fname, "w")
    f.write(str(pubkey.n))
    f.close()

    print(f"        ----- PUBLIC KEY -----")
    print(f"        self.n_pub[{nodeaddr}] = {pubkey.n}")
    print(f"        self.e_pub[{nodeaddr}] = {pubkey.e}")
    print(f"        #----- PRIVATE KEY -----")
    print(f"        self.n_pvt[{nodeaddr}] = {privkey.n}")
    print(f"        self.e_pvt[{nodeaddr}] = {privkey.e}")
    print(f"        self.d_pvt[{nodeaddr}] = {privkey.d}")
    print(f"        self.p_pvt[{nodeaddr}] = {privkey.p}")
    print(f"        self.q_pvt[{nodeaddr}] = {privkey.q}")
    print(f"        self.pvtkey[{nodeaddr}] = PrivateKey(self.n_pvt[{nodeaddr}], self.e_pvt[{nodeaddr}], self.d_pvt[{nodeaddr}], self.p_pvt[{nodeaddr}], self.q_pvt[{nodeaddr}])")

def main():
    nodeaddr = int(sys.argv[1])
    if nodeaddr < 1 or nodeaddr > 255:
        print(f"Invalid node addr {nodeaddr}")
        sys.exit(1)
    setup_rsa(nodeaddr)

if __name__ == "__main__":
    main()
