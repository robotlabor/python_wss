from time import sleep, perf_counter
from threading import Thread
import json
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Pose
from geometry_msgs.msg import PoseArray
from simple_websocket_server import WebSocketServer, WebSocket
from std_msgs.msg import String

IPADDR = '192.168.1.170'
IPADDR = '192.168.1.187'
IPADDR = '192.168.0.87'

device = {0:'PX4', 1:'Husarion1', 2:'Husarion2'}
topicnames = {
                0: ["/PX4_pose","/PX4_destination"], 
                1: ["/rosbot1/PX4_pose","/rosbot1/PX4_destination"],
                2: ["/rosbot2/PX4_pose","/rosbot2/PX4_destination"]
            }
            
#print(device[0])
#print(topicnames[0][1])

pose_ = {}
posedest_ = {}
msgdestination = String()

for value in topicnames:
    pose_[value] = Pose()
    posedest_[value] = PoseArray()


PX4_pose = Pose()
PX4_posearray = PoseArray()
#UTMx_offset = -0.3
#UTMy_offset = -1.5

#UTMx_offset = -0.6
#UTMy_offset = -2.5

#UTMx_offset = -0.3
#UTMy_offset = -2.3

UTMx_offset = -0.7
UTMy_offset = -2.7


rclpy.init(args=None)

def task():
    while (True):
        for value in topicnames:
            print(device[value] + ' position...')
            print(device[value] + " pose x (east) = " + str(pose_[value].position.x))
            print(device[value] + " pose y (north) = " + str(pose_[value].position.y))
        sleep(100)        
        #print('done')


class SimpleEcho(WebSocket):
    def handle(self):
        # handle the message from the client
        global pose_,topicnames,PX4_pose, UTMx_offset, UTMy_offset, topicnames, test_subscriber

        if "get_positions" in self.data:
            # eszközök pozíciójának lekérése ROS hálózatból és válaszban vissza adása a böngészőnek
            #print("valasz = " + str(pose_[0].position.x))
            #print("pose y (north) = " + str(PX4_pose.position.y))
            #print(self.data)
            for value in topicnames:
                if (pose_[value].position.x >0):
                    print( topicnames[value][0] + " position: " + str(pose_[value].position.x) + ", "+ str(pose_[value].position.y))
                x = {
                    "topic": topicnames[value][0],
                    "UTMx": str(pose_[value].position.x+UTMx_offset),
                    "UTMy": str(pose_[value].position.y+UTMy_offset)
                    }

                msg = json.dumps(x)
                if pose_[value].position.x > 0:
                    self.send_message(msg)
            
        elif "set_positions" in self.data:
            # kívánt eszköz
            #print(self.data)
    
            try:
                msg = json.loads(self.data)
                #print(msg)
                global msgdestination

                msgdestination.data = repr(msg)
                
                # a pulbikált bólyák helyének törlése adott idő után
                t5 = Thread(target=erase_wss_destination)
                t5.start()
                t5.join()

                # az üzenetet a golobális PX4_posearray-be dolgozzuk fel, ha

                # melyik topic-ba kell küldeni? Megkapjuk az üzenetben
                # print(msg["topic"])
                #print(msg["positions"])
                #print(len(msg["positions"]))
                #print(msg["positions"]["0"]["utmx"])
                #print(destinationtopic[msg["topic"]])
                print(msg)

                # a topic neve alapján meg kell találni, hogy melyik lesz a hozzá tartozó cél pozíciókat tartalmozó topic 
                postopic = msg["topic"] 
                poslen = len(msg["positions"])
                pa = PoseArray()

                for x in dict(msg["positions"]):
                    #print(msg["positions"][x])
                    #print(msg["positions"]["0"]["utmx"])

                    #beállítjuk a megfelelő globális posearray-t
                    p1 = Pose()
                    p1.position.x = msg["positions"][x]["utmx"]
                    p1.position.y = msg["positions"][x]["utmy"]
                    pa.poses.append(p1)

                #print(pa)

                global posedest_, PX4_posearray
                PX4_posearray = pa
                #print(PX4_posearray)
                deviceid = -1
                x = 0
                for value in topicnames:
                    #print(postopic + " " +topicnames[value][1])
                    if postopic == topicnames[value][1]:
                        deviceid = x
                    x = x + 1    
                    print ("megtalaltam"+ str(deviceid))

                if deviceid >= 0:
                    posedest_[deviceid] = pa
                    print("PoseArray copied")
                    #print( topicnames[value][1] + " position: " + str(pose_[value].position.x) + ", "+ str(pose_[value].position.y))


                #target_destinations = json.loads(json.dumps(msg["positions"]))
                #print(target_destinations["0"])


            except BaseException as err:
                print("Error occurred")
                print(f"Unexpected {err=}, {type(err)=}")

        else:
            print("{}")
            self.send_message(str("{}"))


    def connected(self):
        #global PX4_pose
        print(self.address, 'connected')
        #self.send_message(PX4_pose.position.x)


    def handle_close(self):
        print(self.address, 'closed')


class UTMSubsciber(Node):
    pose = Pose()
    posearray = PoseArray()
    #x: east, y: north
     
    def __init__(self):
        super().__init__('WSS')
        print('WSS')
        #print(topicdestname)
        #self.subscription = self.create_subscription(Pose, topicname, self.utm_callback, 10)

        #self.publisher_ = self.create_publisher(PoseArray, topicdestname, 10)
        #timer_period = 10
        #self.timer = self.create_timer(timer_period, self.utm_callback_publisher)

    def register_topic(self, topicname, topicdestname, deviceid):
        global pose_, posedest_
        print("deviceid: " + str(deviceid))
        print("topic names: "+topicname+" " + topicdestname)
    
        self.subscription = self.create_subscription(Pose, topicname, lambda msg: self.utm_callback(msg, deviceid), 1 )

        #self.publisher_ = self.create_publisher(String, topicdestname, 10)
        #timer_period = 10
        #self.timer = self.create_timer(timer_period, self.utm_callback_publisher)

    def register_publisher(self, topicdestname, deviceid):
        global pose_, posedest_        
        #self.subscription = self.create_subscription(Pose, topicname, lambda msg: self.utm_callback(msg, deviceid), 10 )

        self.publisher_ = self.create_publisher(String, topicdestname, 10)
        timer_period = 5
        self.timer = self.create_timer(timer_period, self.utm_callback_publisher)

    def utm_callback(self, msg, deviceid):
        #print("pose x  = " + str(msg.position.x))
        #print("pose y = " + str(msg.position.y))
		#print("pose z = " + str(msg.position.z))
		#print("orientation x = " + str(msg.orientation.x))
		#print("orientation y = " + str(msg.orientation.y))
		#print("orientation z = " + str(msg.orientation.z))
		#print("orientation w = " + str(msg.orientation.w))
        global pose_
        #topic_ =  self._connection_header['topic']
        #print("uzenet: " + str(deviceid))
        self.pose = msg
        pose_[deviceid] = msg
        #sleep(1)
        #print("pose x (east) = " + str(self.pose.position.x))
        #print("pose y (north) = " + str(self.pose.position.y))


    def utm_callback_publisher(self):
            global posedest_
            global PX4_posearray
            global msgdestination
            #msg = PoseArray()
            #print("publisher uzenet: " + str(deviceid))
 
            #msg = posedest_[0]
            msg = String()
            print(msgdestination)
            msg = msgdestination
            self.publisher_.publish(msg)
            self.get_logger().info('Publishing: "%s"' % msg.data)

	
def subscriber():
    print("Start node")
    global test_subscriber
    
    rclpy.spin(test_subscriber)
    
    #test_subsciber.destroy_node()
    #rclpy.shutdown()


def websocket_server():
    global IPADDR
    server = WebSocketServer(IPADDR, 8001, SimpleEcho)
    #server = WebSocketServer('192.168.0.145', 8001, SimpleEcho)
    server.serve_forever()


test_subscriber = UTMSubsciber()

for value in topicnames:
    #print(topicnames[value][0])
    test_subscriber.register_topic(topicnames[value][0], topicnames[value][1], value)
    #test_subscriber.register_topic('/PX4_pose','/PX4_destination')
    #test_subscriber.register_topic('/Husarion_pose','/Husarion_destination')

#test_subscriber.register_publisher(topicnames[0][1], value)
test_subscriber.register_publisher("/WSS_destination", value)


def erase_wss_destination():
    global msgdestination
    sleep(10)
    msgdestination.data = ""
    print("WSS destination has been erased")


#start_time = perf_counter()
try:
    # create two new threads
    t1 = Thread(target=websocket_server)
    #px4thread = subscriber('/PX4_pose','PX4_destination')
    #t2 = Thread(target=subscriber, args=('/PX4_pose','PX4_destination'))
    t2 = Thread(target=subscriber)
    t3 = Thread(target=task)

    #t4 = Thread(target=subscriber, args=('/Husarion_pose','Husarion_destination'))
    #t4 = Thread(target=publisher)

    # start the threads
    t1.start()
    t2.start()
    t3.start()
    #t4.start()
    #t4.start()

    # wait for the threads to complete
    t1.join()
    t2.join()
    t3.join()
    #t4.join()
    #t4.join()

    #end_time = perf_counter()
    #print(f'It took {end_time- start_time: 0.2f} second(s) to complete.')
except KeyboardInterrupt:
    test_subscriber.destroy_node()
    rclpy.shutdown()
    #TODO: close ws server and loop correctely
    print("Exiting program...")