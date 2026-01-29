import math

ER = 6366707.0195 #Earth Radius in Meters
RANGE = 40        #maximum distance for communication in meters

# https://en.wikipedia.org/wiki/Haversine_formula
def haversine(p1, p2):
    lat1, lon1, lat2, lon2 = map(math.radians, [p1[0], p1[1], p2[0], p2[1]])
    a = math.sin((lat2 - lat1)/2)**2
    b = math.cos(lat1)
    c = math.cos(lat2)
    d = math.sin((lon2 - lon1)/2)**2
    return 2*ER*math.asin(math.sqrt(a+(b*c*d)))


def coord_to_real(coord):
    x = ER * math.cos(coord[1]) * math.cos(coord[0])
    y = ER * math.cos(coord[1]) * math.sin(coord[0])
    z = ER * math.sin(coord[1])
    return (x, y, z)

class node:
    def __init__(self, id, lat, lon):
        self.id = id
        self.update_location(lat, lon)
        self.tree = None
    
    def update_location(self, lat: float, lon: float):
        self.lat = lat
        self.lon = lon
        # (x, y, z) = coord_to_real((self.lat, self.lon))
        # self.x = x
        # self.y = y
        # self.z = z

    def remove(self):
        if self.tree != None:
            self.tree.points.remove(self)
            self.tree.update_center()
        self.tree = None
    
    def get_coord(self) -> tuple[float, float]:
        return (self.lat, self.lon)
    
    def get_pos(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)
    
class balltree:
    def __init__(self):
        self.left = None
        self.right = None
        self.center = None
        self.radius = 0
        self.points = []

    def insert(self, n : node, leaf_size = 5):
        if self.center is None:
            self.center = n
            self.points.append(n)
            n.tree = self
            return
        
        # if self.center.id is None and len(self.points) < 1:
        #     self.center = n
        #     self.points.append(n)
        #     return

        if len(self.points) < leaf_size:
            self.points.append(n)
            n.tree = self
            self.update_center()
        else:
            if self.left is None or self.right is None:
                self.split()

            if self.distance(n, self.left.center) < self.distance(n, self.right.center):
                self.left.insert(n, leaf_size)
            else:
                self.right.insert(n, leaf_size)

            self.radius = max(self.radius, self.distance(self.center, n))

    def split(self):
        lon_variance = self.variance([p.lon for p in self.points])
        lat_variance = self.variance([p.lat for p in self.points])
        axis = 0 if lon_variance >= lat_variance else 1  # 0 lon, 1 lat

        self.points.sort(key=lambda p: (p.lon, p.lat)[axis])
        median = len(self.points) // 2

        self.left = balltree()
        self.left.points = self.points[:median]
        self.left.update_center()
        for p in self.left.points:
            p.tree = self.left

        self.right = balltree()
        self.right.points = self.points[median:]
        self.right.update_center()
        for p in self.right.points:
            p.tree = self.right

        self.points = []

    def update_center(self):
        if not self.points:
            return
        lon = sum(p.lon for p in self.points) / len(self.points)
        lat = sum(p.lat for p in self.points) / len(self.points)
        self.center = node(None, lat, lon)
        self.radius = max(self.distance(self.center, p) for p in self.points)

    @staticmethod
    def variance(values):
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)
        
    def calculate_center(self, points):
        lon = sum(p.lon for p in points) / len(points)
        lat = sum(p.lat for p in points) / len(points)
        return node(None, lat, lon)
    
    def distance(self, node1, node2):
        #return math.sqrt((node1.lon - node2.lon) ** 2 + (node1.lat - node2.lat) ** 2)
        return haversine((node1.lat, node1.lon), (node2.lat, node2.lon))

    def find(self, point : node, radius : float, results=None):
        if results is None:
            results = []
        
        if self.center is None:
            return results
        
        dist_to_center = self.distance(self.center, point)
        # print(f'search point {point.id} has dist to {self.center.id} {dist_to_center}')
        if dist_to_center - self.radius <= radius:
            if self.points:
                results.extend(p for p in self.points if self.distance(p, point) <= radius)
            if self.left:
                self.left.find(point, radius, results)
            if self.right:
                self.right.find(point, radius, results)
        
        return results
    
class quadtree:
    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.radius = radius

        self.has_split = False
        self.n = None

        self.py_px = None
        self.py_mx = None
        self.my_px = None
        self.my_mx = None

    def inside(self, p):
         return (self.x - self.radius <= p[0] <= self.x + self.radius and
                 self.y - self.radius <= p[1] <= self.y + self.radius)
    
    def sphere_intersecting_cube(self, sphere_x, sphere_y, sphere_radius):
        if (self.x - self.radius <= sphere_x <= self.x + self.radius and
            self.y - self.radius <= sphere_y <= self.y + self.radius):
            return True
        
        closest_x = max(self.x - self.radius, min(sphere_x, self.x + self.radius))
        closest_y = max(self.y - self.radius, min(sphere_y, self.y + self.radius))
        distance = math.sqrt((closest_x - sphere_x) ** 2 +
                            (closest_y - sphere_y) ** 2)
        return distance <= sphere_radius
    
    def point_in_sphere(self, sphere_x, sphere_y, sphere_radius):
        x, y = self.n.get_coord()
        distance = math.sqrt((x - sphere_x) ** 2 +
                            (y - sphere_y) ** 2)
        return distance <= sphere_radius
    
    def find(self, pos: tuple[float, float]):
        if not self.has_split:
            if self.n != None:
                if self.point_in_sphere(pos[0], pos[1], RANGE):
                    return [self.n]
                return []
            return []
        out = []
        out.extend(self.py_px.find(pos))
        out.extend(self.py_mx.find(pos))
        out.extend(self.my_px.find(pos))
        out.extend(self.my_mx.find(pos))
        return out

    def insert(self, n: node):
        if not self.inside(n.get_coord()):
            return
        
        if not self.has_split:
            if self.n == None:
                self.n = n
                self.n.tree = self
                return
            self.split()
            self.insert(self.n)
            self.n = None
            self.insert(n)
            return

        self.py_px.insert(n)
        self.py_mx.insert(n)
        self.my_px.insert(n)
        self.my_mx.insert(n)

    def split(self):
        self.has_split = True
        new_radius = self.radius / 2
        offsets = [-new_radius, new_radius]

        self.py_px = octree(self.x + offsets[1], self.y + offsets[1], new_radius)
        self.py_mx = octree(self.x + offsets[0], self.y + offsets[1], new_radius)
        self.my_px = octree(self.x + offsets[1], self.y + offsets[0], new_radius)
        self.my_mx = octree(self.x + offsets[0], self.y + offsets[0], new_radius)

class octree:
    def __init__(self, x, y, z, radius):
        self.x = x
        self.y = y
        self.z = z
        self.radius = radius

        self.has_split = False
        self.n = None

        self.py_px_mz = None
        self.py_px_pz = None
        self.py_mx_pz = None
        self.py_mx_mz = None
        
        self.my_px_pz = None
        self.my_px_mz = None
        self.my_mx_pz = None
        self.my_mx_mz = None

    def inside(self, p):
         return (self.x - self.radius <= p[0] <= self.x + self.radius and
                 self.y - self.radius <= p[1] <= self.y + self.radius and
                 self.z - self.radius <= p[2] <= self.z + self.radius)
    
    def sphere_intersecting_cube(self, sphere_x, sphere_y, sphere_z, sphere_radius):
        closest_x = max(self.x - self.radius, min(sphere_x, self.x + self.radius))
        closest_y = max(self.y - self.radius, min(sphere_y, self.y + self.radius))
        closest_z = max(self.z - self.radius, min(sphere_z, self.z + self.radius))
        distance = math.sqrt((closest_x - sphere_x) ** 2 +
                            (closest_y - sphere_y) ** 2 +
                            (closest_z - sphere_z) ** 2)
        return distance <= sphere_radius
    
    def point_in_sphere(self, sphere_x, sphere_y, sphere_z, sphere_radius):
        x, y, z = self.n.get_pos()
        distance = math.sqrt((x - sphere_x) ** 2 +
                            (y - sphere_y) ** 2 +
                            (z - sphere_z) ** 2)
        return distance <= sphere_radius
    
    def find(self, pos: tuple[float, float, float]):
        if not self.has_split:
            if self.n != None:
                if self.point_in_sphere(pos[0], pos[1], pos[2], RANGE):
                    return [self.n]
                return []
            return []
        out = []
        out.extend(self.py_px_pz.find(pos))
        out.extend(self.py_px_mz.find(pos))
        out.extend(self.py_mx_pz.find(pos))
        out.extend(self.py_mx_mz.find(pos))

        out.extend(self.my_px_pz.find(pos))
        out.extend(self.my_px_mz.find(pos))
        out.extend(self.my_mx_pz.find(pos))
        out.extend(self.my_mx_mz.find(pos))
        return out

    def insert(self, n: node):
        if not self.inside(n.get_pos()):
            return
        
        if not self.has_split:
            if self.n == None:
                self.n = n
                self.n.tree = self
                return
            self.split()
            self.insert(self.n)
            self.n = None
            self.insert(n)
            return

        self.py_px_pz.insert(n)
        self.py_px_mz.insert(n)
        self.py_mx_pz.insert(n)
        self.py_mx_mz.insert(n)
        
        self.my_px_pz.insert(n)
        self.my_px_mz.insert(n)
        self.my_mx_pz.insert(n)
        self.my_mx_mz.insert(n)

    def split(self):
        self.has_split = True
        new_radius = self.radius / 2
        offsets = [-new_radius, new_radius]

        self.py_px_pz = octree(self.x + offsets[1], self.y + offsets[1], self.z + offsets[1], new_radius)
        self.py_px_mz = octree(self.x + offsets[1], self.y + offsets[1], self.z + offsets[0], new_radius)
        self.py_mx_pz = octree(self.x + offsets[0], self.y + offsets[1], self.z + offsets[1], new_radius)
        self.py_mx_mz = octree(self.x + offsets[0], self.y + offsets[1], self.z + offsets[0], new_radius)
        self.my_px_pz = octree(self.x + offsets[1], self.y + offsets[0], self.z + offsets[1], new_radius)
        self.my_px_mz = octree(self.x + offsets[1], self.y + offsets[0], self.z + offsets[0], new_radius)
        self.my_mx_pz = octree(self.x + offsets[0], self.y + offsets[0], self.z + offsets[1], new_radius)
        self.my_mx_mz = octree(self.x + offsets[0], self.y + offsets[0], self.z + offsets[0], new_radius)