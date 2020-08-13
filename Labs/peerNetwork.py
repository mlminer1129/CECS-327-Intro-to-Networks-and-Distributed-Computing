'''
Peer to Peer file sharing program

@authors
Salvador Gallardo
010098489

John Minor
003047679

CECS 327 Summer 2020
'''

#import needed libraries 
import socket
import threading
import sys
import os
import time
import random 

#this class contains assigned the IP to peers for global use
class Network:
    #peers = [socket.gethostbyname(socket.gethostname())]
    peers = ['192.168.1.7']

#this class allows a single node to implement the server and then become a client
class ServerMode:
    peer_conn = [] #save connections of nodes
    peer_addr = [] #save names of nodes connected 
    
    #runs at the create of object, creates a server and client
    def __init__(self):
        #create the socket and allow it to be reused
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        #bind the address to the socket
        print('[SERVER] starting @ 192.168.1.7)') #, socket.gethostbyname(socket.gethostname()))
        #self.s.bind((socket.gethostbyname(socket.gethostname()), 5050))
        self.s.bind(('192.168.1.7', 5050))
        
        #place up to 10 connections on backlog
        self.s.listen(10)
        print("[SERVER] now listening...")
        
        #start a thread to make the server also a client 
        clientThread = threading.Thread(target=self.beClient, args=(self.s,))
        clientThread.daemon = True
        clientThread.start()
        
        #continously listen and accept connections
        while True:
            #accept incoming connection
            conn, addr = self.s.accept()
            
            #start a thread to listen to connected client 
            connThread = threading.Thread(target=self.reciever, args=(conn, addr))
            connThread.daemon = True
            connThread.start()
            
            #add the connection and address to the lists
            self.peer_conn.append(conn)
            self.peer_addr.append(addr[0])
            print('[SERVER]', str(addr[0]) + ':' + str(addr[1]), " connected.")
            #notifiy peers of conection
            self.broadcast()
    
    #receives incoming data
    def reciever(self, conn, addr):
        try:
            while True:
            #read in data from socket
                data = conn.recv(1024)
                for connection in self.peer_conn:
                #relay message
                    connection.send(data)
            
            #if no data was read
                if not data:
                #remove connection and address from list and close connection
                    print(str(addr[0]) + ':' + str(addr[1]), " disconnected.")
                    self.peer_conn.remove(conn)
                    self.peer_addr.remove(addr[0])
                    conn.close()
                    self.send_peers()
                    break
        except Exception:
            sys.exit()
        
    
    #broadcast newly connected peer info
    def broadcast(self):
        #read all addresses 
        p = ""
        for peer in self.peer_addr:
            p = p + peer + ","
        
        #send addresses to all peers
        for connection in self.peer_conn:
            connection.send(b'\x11' + bytes(p, 'utf-8'))

    #create a client object for Server's client thread
    def beClient(self, s):
        for peer in Network.peers:
            try:
                client = ClientMode(peer)
            except KeyboardInterrupt:
                sys.exit(0)

#this class is for a nodes client implementation
class ClientMode:

    #runs at creation of object and attempts to connect to server 
    def __init__(self, address):
        try:
            self.subscribed = [] #keep track of current files subscribed to
            self.provider = []  #files currently hosting
        
            #create socket and allow for reuse 
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
            #connect to the socket 
            #s.connect((socket.gethostbyname(socket.gethostname()), 5050))
            s.connect(('192.168.1.7', 5050))
        

            #create a thread to send messages 
            iThread = threading.Thread(target=self.send_msg, args=(s,))
            iThread.daemon = True
            iThread.start()

            #grab own address and save the second element holding port number
            self.ID = s.getsockname()[1]
            self.path = os.getcwd() + '\\node' + str(self.ID)
            os.mkdir(self.path , 755)
        
        except Exception:
            sys.exit()
        
        #loop repeatedly to receive data 
        try:
            while True:
                #read data from socket
                data = s.recv(1024)
                if not data:
                    print('breaking from loop')
                    break
                #if message was a list of peers, update peers
                if data[0:1] == b'\x11':
                    self.update_peers(data[1:])
                    #else handle file request
                else:
                    msg = str(data, 'utf-8')

                    #grab the header with the file name
                    name = msg.split('\n', 1)[0]
                    
                    #grab remaining content
                    if name in self.subscribed:
                        content = msg.split('\n', 1)[1]
                        
                        #if another node requested file , try to share file
                        if content == 'REQUEST':
                            
                            if name in self.provider:
                                print('got request for my file')
                                p = self.path + '\\' + name
                                f = open(p, 'r')
                                name = name +'\n'
                                content = name + f.read()
                                s.send(bytes(content , 'utf-8'))
                        
                        #else a file is being published 
                        else:
                            p = self.path + '\\'+ name
        
                            #write the downloaded file
                            f = open(p, 'w')
                            f.write(content)
                            f.close()

        except Exception:
            sys.exit()
            
    #update list of peers
    def update_peers(self, peer_data):
        Network.peers = str(peer_data, 'utf-8').split(",")[:-1]

    #send request to peers
    def send_msg(self, s):
        while True:

            print('Files:', self.subscribed)
            print('Peer ID:', self.ID)
            choice = int(input("Menu: \n1) Publish File \n2) File Subscribe \n3) Quit\n"))
            
            if choice == 1:

                #get input for file to upload and set path
                newFile = input("Enter file:")
                newFile = newFile + '.txt'
                p = self.path + '\\' + newFile
                

                #open contents of file to be uploaded
                try:
                    f = open(p, 'r')
                    #add to list as hosting this file
                    self.provider.append(newFile)
                    #subscribe for future updates
                    self.subscribed.append(newFile)
                    
                    #read file and send to peers
                    newFile = newFile + '\n'
                    newFile = newFile + f.read()
                    s.send(bytes(newFile , 'utf-8'))
                except:
                    print(p, 'not found.')
                
            elif choice == 2:
                search = input("Search: ")
                search = search+'.txt'
                self.subscribed.append(search)
                search = search + '\nREQUEST'
                
                s.send(bytes(search, 'utf-8'))
                
            elif choice == 3:
                try:
                    self.quit(s)
                    break
                except Exception:
                    sys.exit()

    #quit connection
    def quit(self, s):
        print("Disconnected...")
        s.shutdown(self.SHUT_DR)
        s.close()
        sys.exit()


if __name__ == "__main__":
    
    while True:
        try:
            
            time.sleep(random.randint(1, 5))
            for peer in Network.peers:
                try:
                    client = ClientMode(peer)
                except KeyboardInterrupt:
                    sys.exit(0)
                except:        
                    pass
                
                try:
                    server = ServerMode()
                except KeyboardInterrupt:
                    sys.exit()
                except:
                    pass
                
        except KeyboardInterrupt as e:
            sys.exit(0)
    


