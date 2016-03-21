import time
import ast
import hashlib
import socket
import re
import sqlite3
import os
import sys

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto import Random

if os.path.isfile("keys.pem") is True:
    print "keys.pem found"

else:   
    #generate key pair and an address
    random_generator = Random.new().read
    key = RSA.generate(1024, random_generator)
    public_key = key.publickey()

    private_key_readable = str(key.exportKey())
    public_key_readable = str(key.publickey().exportKey())
    address = hashlib.sha224(public_key_readable).hexdigest() #hashed public key
    #generate key pair and an address

    print "Your address: "+ str(address)
    print "Your private key:\n "+ str(private_key_readable)
    print "Your public key:\n "+ str(public_key_readable)

    pem_file = open("keys.pem", 'a')
    pem_file.write(str(private_key_readable)+"\n"+str(public_key_readable) + "\n\n")
    pem_file.close()
    address_file = open ("address.txt", 'a')
    address_file.write(str(address)+"\n")
    address_file.close()


# import keys
key_file = open('keys.pem','r')
key = RSA.importKey(key_file.read())
public_key = key.publickey()
private_key_readable = str(key.exportKey())
public_key_readable = str(key.publickey().exportKey())
address = hashlib.sha224(public_key_readable).hexdigest()

print "Your address: "+ str(address)
print "Your private key:\n "+ str(private_key_readable)
print "Your public key:\n "+ str(public_key_readable)
# import keys


#open peerlist and connect
with open ("peers.txt", "r") as peer_list:
    peers=peer_list.read()
    peer_tuples = re.findall ("'([\d\.]+)', '([\d]+)'",peers)
    print peer_tuples

for tuple in peer_tuples:
    HOST = tuple[0]
    #print HOST
    PORT = int(tuple[1])
    #print PORT

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #s.settimeout(5)
        s.connect((HOST, PORT))
        print "Connected to "+str(HOST)+" "+str(PORT)
        #network client program

        s.sendall('Hello, server')

        peer = s.getpeername()
        data = s.recv(1024) #receive data
        print 'Received data from '+ str(peer) +"\n"+ str(data)

        #get remote peers into tuples
        server_peer_tuples = re.findall ("'([\d\.]+)', '([\d]+)'",data)
        print server_peer_tuples
        print len(server_peer_tuples)
        #get remote peers into tuples

        #get local peers into tuples
        peer_file = open("peers.txt", 'r')
        peer_tuples = []
        for line in peer_file:
            extension = re.findall ("'([\d\.]+)', '([\d]+)'",line)
            peer_tuples.extend(extension)
        peer_file.close()
        print peer_tuples
        #get local peers into tuples

        for x in server_peer_tuples:
            if x not in peer_tuples:
                print str(x)+" is a new peer, saving."

                peer_list_file = open("peers.txt", 'a')
                peer_list_file.write(x+"\n")
                peer_list_file.close()        
                
            else:
                print str(x)+" is not a new peer, skipping."

        #broadcast
                
        #send tx
        to_address = str(raw_input ("Send to address: "))
        amount = str(raw_input ("How much to send: "))
                
        try: #start constructing new tx
            conn = sqlite3.connect('ledger.db')
            c = conn.cursor()
            c.execute("SELECT block_height FROM transactions ORDER BY block_height DESC LIMIT 1;")
            block_height = int(c.fetchone()[0])           
            block_height_new = block_height+1

            #sync from node
            #request block update
            s.sendall (str(block_height))
            #request block update
                
            block_difference = s.recv(1024)
            i = 1
            if str(block_difference) != "No new blocks here":
                print "Receiving "+block_difference+" steps to sync"
                                
                while int(i) <= int(block_difference): #while blocks are not synced
                    sync = s.recv(1024)
                    i = i+1
                    #verify
                    sync_list = ast.literal_eval(sync) #this is great, need to add it to client -> node sync
                    received_block_height = sync_list[0]
                    received_address = sync_list[1]
                    received_to_address = sync_list[2]
                    received_amount = sync_list [3]
                    received_signature = sync_list[4]
                    received_public_key_readable = sync_list[5]
                    received_public_key = RSA.importKey(sync_list[5])
                    received_txhash = sync_list[6]
                    received_transaction = str(received_block_height) +":"+ str(received_address) +":"+ str(received_to_address) +":"+ str(received_amount) #todo: why not have bare list instead of converting?
                    received_signature_tuple = ast.literal_eval(received_signature) #converting to tuple

                     ######wip / compare db and received txhash(db+1) TODO

                            
                    c.execute("SELECT txhash FROM transactions ORDER BY block_height DESC LIMIT 1;")
                    txhash = c.fetchone()[0]
                    print "Last db txhash: "+str(txhash)
                    print "Received txhash: "+str(received_txhash)

                    for row in c.execute('SELECT * FROM transactions ORDER BY block_height'):
                        db_block_height = row[0]
                        db_address = row[1]
                        db_to_address = row[2]
                        db_amount = row [3]
                        #db_signature = row[4]
                        #db_public_key = RSA.importKey(row[5])
                        db_txhash = row[6]                        
                        db_transaction = str(db_block_height) +":"+ str(db_address) +":"+ str(db_to_address) +":"+ str(db_amount)
                        
                    if received_txhash == hashlib.sha224(db_transaction+txhash).hexdigest():
                        print "txhash valid"
                        txhash_new = hashlib.sha224(received_transaction+received_txhash).hexdigest() #define new tx hash based on previous
                    else:
                        print "txhash invalid"
                   
                        ######wip TODO
                    


                        
                    if received_public_key.verify(received_transaction, received_signature_tuple) == True:
                        print "Received step "+str(received_block_height)+" is valid"
                        try:                    
                            conn = sqlite3.connect('ledger.db')
                            c = conn.cursor()
                            print "Verifying balance"
                            print received_address
                            c.execute("SELECT sum(amount) FROM transactions WHERE to_address = '"+received_address+"'")
                            credit = c.fetchone()[0]
                            c.execute("SELECT sum(amount) FROM transactions WHERE address = '"+received_address+"'")
                            debit = c.fetchone()[0]
                            if debit == None:
                                debit = 0
                            if credit == None:
                                credit = 0                                
                            print "Total credit: "+str(credit)                                
                            print "Total debit: "+str(debit)
                            balance = int(credit) - int(debit)
                            print "Transction address balance: "+str(balance)
                        except sqlite3.Error, e:                      
                            print "Error %s:" % e.args[0]
                            sys.exit(1)                        
                        finally:                        
                            if conn:
                                conn.close()
                                
                        if  int(balance) - int(amount) < 0:
                            print "Their balance is too low for this transaction"
        
                        
                        else:
                            #verify
                                
                            #save step to db
                            try:
                                conn = sqlite3.connect('ledger.db') 
                                c = conn.cursor()
                                c.execute("INSERT INTO transactions VALUES ('"+str(received_block_height)+"','"+str(received_address)+"','"+str(received_to_address)+"','"+str(received_amount)+"','"+str(received_signature)+"','"+str(received_public_key_readable)+"','"+str(received_txhash)+"')") # Insert a row of data
                                print "Ledger updated with a received transaction"
                                conn.commit() # Save (commit) the changes
                                
                            except sqlite3.Error, e:                        
                                print "Error %s:" % e.args[0]
                                sys.exit(1)                        
                            finally:                        
                                if conn:
                                    conn.close()
                            #save step to db
                        print "Ledger synchronization finished"
                    
                #sync from node
            
        except sqlite3.Error, e:                        
            print "Error %s:" % e.args[0]
            sys.exit(1)                        
        finally:                        
            if conn:
                conn.close()       

        transaction = str(block_height_new) +":"+ str(address) +":"+ str(to_address) +":"+ str(amount)
        signature = key.sign(transaction, '')
        print "Signature: "+str(signature)

    

        if public_key.verify(transaction, signature) == True:

            ###todo2 (we still need to verify with node, or is reject enough?)
            conn = sqlite3.connect('ledger.db')
            c = conn.cursor()
            c.execute("SELECT txhash FROM transactions ORDER BY block_height DESC LIMIT 1;")
            txhash = str(c.fetchone()[0])
            txhash_new = hashlib.sha224(transaction+txhash).hexdigest() #define new tx hash based on previous
            print "New txhash to go with your transaction: "+txhash_new
            conn.close()
            ###todo2
            print "The signature and control txhash is valid, proceeding to send transaction, signature, new txhash and the public key"           
            s.sendall(transaction+";"+str(signature)+";"+public_key_readable+";"+str(txhash_new))

            
        else:
            print "Invalid signature"
        #send tx

   
            
        #broadcast
        s.close()

        #network client program


    except Exception as e:
        print e
        print "Cannot connect to "+str(HOST)+" "+str(PORT)
        raise
