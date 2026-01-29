from flask import Flask, render_template, request
from flask_socketio import SocketIO
from markupsafe import escape
import json
import math
from octree import node, octree, quadtree, balltree

UPDATE_RANGE = 3
RANGE = 10000        #maximum distance for communication in meters
ER = 6366707.0195 #Earth Radius in Meters

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

clients = {}

# tree = octree(0, 0, 0, ER*1.1)
tree = balltree()

USETREE = True

# https://en.wikipedia.org/wiki/Haversine_formula
def haversine(p1, p2):
    lat1, lon1, lat2, lon2 = map(math.radians, [p1[0], p1[1], p2[0], p2[1]])
    a = math.sin((lat2 - lat1)/2)**2
    b = math.cos(lat1)
    c = math.cos(lat2)
    d = math.sin((lon2 - lon1)/2)**2
    return 2*ER*math.asin(math.sqrt(a+(b*c*d)))

def find_targets(id):
    n = clients[id]
    targets = []
    if USETREE:
        o = tree.find(n, RANGE)
        s = {}
        for t in o:
            if t.id is not None:
                s[t.id] = t
                # print(f'found {t.id}')
        for i, p in s.items():
            targets.append(i)
        # print(f'found {len(targets)} nearby {n.get_coord()} {n.id}')
    else:
        for i, o in clients.items():
            dist = haversine(n.get_coord(), o.get_coord())
            # print (f"people are {dist}m apart")
            if  dist < RANGE:
                targets.append(i)
    return targets

@app.route('/')
def home():
    return render_template('index.html')

@socketio.on('connect')
def test_connect(auth):
    print("Client connected")

@socketio.on('disconnect')
def test_disconnect():
    if request.sid in clients:
        clients[request.sid].remove()
        del clients[request.sid]


@socketio.on('join')
def join(content):
    data = json.loads(content)
    if data['id'] not in clients:
        clients[data['id']] = node(data['id'], data['lat'], data['lon'])
    if USETREE:
        # clients[data['id']].remove()
        tree.insert(clients[data['id']])

@socketio.on('send')
def message(content):
    data = json.loads(content)
    if 'id' not in data:
        data['id'] = request.sid
    if data['id'] not in clients:
        clients[data['id']] = node(data['id'], data['lat'], data['lon'])
        if USETREE:
            tree.insert(clients[data['id']])
    else:
        if haversine((clients[data['id']].lat, clients[data['id']].lon), 
                     (data['lat'], data['lon'])) > UPDATE_RANGE:
            clients[data['id']].update_location(data['lat'], data['lon'])
            if USETREE:
                #tree.build_tree(tree.points)
                clients[data['id']].remove()
                tree.insert(clients[data['id']])
    out = {}
    out['from'] = data['id']
    out['msg'] =  data['msg']
    if out['msg'] == '':
        socketio.emit('bad', 'Cannot Send Empty Message', to=data['id'])
        return
    if len(out['msg']) > 256:
        socketio.emit('bad', 'Cannot Send Message Longer Than 256 Chars', to=data['id'])
        return
    pl = json.dumps(out)
    targets = find_targets(data['id'])
    for t in targets:
        socketio.emit('receive', pl, to=t)

@socketio.on('status')
def update(content):
    data = json.loads(content)
    if 'id' not in data:
        data['id'] = request.sid
    if data['id'] not in clients:
        clients[data['id']] = node(data['id'], data['lat'], data['lon'])
    else:
        if haversine((clients[data['id']].lat, clients[data['id']].lon), 
                     (data['lat'], data['lon'])) > UPDATE_RANGE:
            clients[data['id']].update_location(data['lat'], data['lon'])
            if USETREE:
                #tree.build_tree(tree.points)
                # print("updating value")
                clients[data['id']].remove()
                tree.insert(clients[data['id']])
    socketio.emit('nearby', json.dumps({'count': len(find_targets(data['id']))-1}), to=data['id'])

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', ssl_context='adhoc')