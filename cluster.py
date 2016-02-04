from __future__ import division

try:
    from scipy import zeros, mean
    from scipy.spatial.distance import sqeuclidean, squareform, pdist
    SCIPY = True
except ImportError:
    SCIPY = False    
    
import random
import copy
import itertools


class Results():
    def __init__(self, sil, clusters):
        self.sil = sil
        self.clusters = clusters


class Point:
    """The Point class represents points in n-dimensional space"""
    # Instance variables
    # self.coords is a list of coordinates for this Point
    # self.n is the number of dimensions this Point lives in (ie, its space)
    # self.item is an object bound to this Point
    # Initialize new Points
    def __init__(self, coords, item=None):
        self.coords = coords
        self.n = len(coords)
        self.item = item
        if item != None:
            self.id = item.id

    def __repr__(self):
        if self.item != None:
            return str(self.item.id)
        else:
            return "synthetic point"
        
    def __len__(self):
        return self.n

    def __deepcopy__(self, memo):
        # When we do a deep copy of a point, we only need to copy the coords.
        # In particular, we don't want to copy the item.
        return Point(copy.deepcopy(self.coords, memo), self.item)


class Cluster:
    """The Cluster class represents clusters of points in n-dimensional space"""

    def __init__(self, points):
        if len(points) == 0: 
            raise Exception("Empty cluster")
        self.points = points
        self.n = points[0].n
        self.centroid = self.calculate_centroid()

    def __len__(self):
        return len(self.points)

    def update(self, points):
        """
        Update function for the K-means algorithm. Assigns a new list
        of Points to this Cluster and returns centroid difference.
        """
        old_centroid = self.centroid
        self.points = points
        self.centroid = self.calculate_centroid()
        return get_distance(old_centroid, self.centroid)
  
    def calculate_centroid(self):
        """Returns the average of all Points in the Cluster"""
        return get_average_point(self.points)

    def finalize(self):
        """ Finds the nearest item to the centroid."""
        centroid_dist = lambda x:get_distance(self.centroid, x)
        self.nearest_point = min(self.points, key=centroid_dist)                              

    def get_metrics(self, top_attributes, clusters):
        """
        Calculate the cohesion and overlap of each attribute in the top
        fatures.  Cohesion is the percentage of items in this cluster
        that have contain the attribute.  Overlap is the percentage of
        items in all other clusters that contain the attribute.
        """
        num_top_feats = len(top_attributes)
        cohesions = [0] * num_top_feats
        overlaps = [0] * num_top_feats
        all_items = 0
        for cluster in clusters:
            for point in cluster.points:
                all_items += 1
                for i,feat in enumerate(top_attributes):            
                    if feat in point.item.attributes:
                        if cluster is self:
                            cohesions[i] += 1
                        else:
                            overlaps[i] += 1
        this_items = len(self)
        other_items = all_items - this_items
        return [(f, c/this_items, o/other_items) 
                for f,c,o in zip(top_attributes, cohesions, overlaps)]


def get_distance_scipy(a, b):
    """Get the squared Euclidean distance between two Points using scipy"""
    return sqeuclidean(a.coords, b.coords)

    
def get_distance_manual(a, b):
    """Get the squared Euclidean distance between two Points"""
    return sum((c1-c2)**2 for c1, c2 in 
               itertools.izip(a.coords, b.coords) if c1 != c2)


def get_all_distances_scipy(points):
    """Calculate the squared Euclidean distance between all points using scipy"""
    matrix = squareform(pdist([p.coords for p in points], 'sqeuclidean'))
    distances = {}
    for i,m in enumerate(points):
        for j,n in enumerate(points[:i]):
            distances[(m.id, n.id)] = matrix[i][j]
    return distances
    

def get_all_distances_manual(points):
    """Calculate the squared Euclidean distance between all points."""
    distances = {}
    for x,y in itertools.combinations(points,2):
        dist = get_distance_manual(x, y)
        distances[(x.id, y.id)] = dist
    return distances


def get_average_point_scipy(points):
    return Point(mean([p.coords for p in points], axis=0))


def get_average_point_manual(points):
    num_points = len(points[0])
    average_coords = [0]*num_points
    for i in range(num_points):
        tot = sum(point.coords[i] for point in points)
        average_coords[i] = tot / num_points
    return Point(average_coords)


if SCIPY:
    get_all_distances = get_all_distances_scipy
    get_average_point = get_average_point_scipy
    get_distance = get_distance_scipy
else:
    get_all_distances = get_all_distances_manual
    get_average_point = get_average_point_manual
    get_distance = get_distance_manual


def random_clustering(points, k):
    """Assign points randomly into k roughly equal sized Clusters""" 
    def chunks(l, n):
        """ Yield n successive chunks from l."""
        newn = int(len(l) / n)
        for i in xrange(0, n - 1):
            yield l[i*newn:i*newn+newn]
        yield l[n*newn-newn:]
    random.shuffle(points)
    clusters = [Cluster(chunk) for chunk in chunks(points, k)]
    for cluster in clusters:
        cluster.finalize()
    return clusters


def get_seeds_det(points, k):
    """
    Select k seeds from a list deterministically. Intended to provide
    consistent output for testing purposes
    """
    return points[:k]


def get_seeds(points, k):
    """
    Seeds are selected like this: The first seed is taken at random,
    the second is the furthest point from the initial seed. The third
    is the furthest from the average of points 1 and 2... the nth is
    the furthers point away from the average of the first n-1 points.
    """
    p = random.choice(points)
    points = [x for x in points if x is not p]
    initial_points = [p]
    for i in range(k - 1):
        average_point = get_average_point(initial_points)
        dist_from_avrg = lambda x:get_distance(average_point, x)
        max_point = max(points, key=dist_from_avrg)
        initial_points.append(max_point)
        points = [x for x in points if x is not max_point]
    return initial_points


def kmeans(points, k):
    """Return Clusters of Points formed by K-means clustering"""
    clusters = [Cluster([point]) for point in get_seeds(points, k)]
    iterations = 0
    while True:
        # temp list for each Cluster
        lists = [[] for x in range(k)]
        for point in points:
            # determine which Cluster's centroid is nearest
            index = 0
            min_distance = get_distance(point, clusters[0].centroid)
            for i, cluster in enumerate(clusters[1:]):
                distance = get_distance(point, cluster.centroid)
                if distance < min_distance:
                    min_distance = distance
                    index = i + 1
            lists[index].append(point)
        # Update each Cluster with the corresponding list
        converged = True
        for i, cluster in enumerate(clusters):
            # if cluster becomes empty, drop it
            if lists[i] == []:
                lists.pop(i)
                clusters.pop(i)
                k -= 1
                print "Dropped empty cluster" 
            else:
                shift = cluster.update(lists[i])
                if shift != 0:
                    converged = False
        if converged: 
            break
        iterations += 1
    for cluster in clusters:
        cluster.finalize()
    return clusters, iterations


def get_points(pdiff, items):
    """
    For each item: create a attribute vector containing
    the union of attributes across all the results for that item.
    """ 
    observations = []
    num_attributes = len(pdiff.attributes)
    for item in items:
        if len(item.results) == 0:
            continue
        if SCIPY:
            attribute_vector = zeros(num_attributes)
        else:
            attribute_vector = [0]*num_attributes
        for i, attribute in enumerate(pdiff.attributes.values()):
            for result in item.results:
                if attribute.name in result.attributes:
                    attribute_vector[i] = attribute.cluster_weight
                    break
        observations.append(Point(attribute_vector, item))
    return observations


def get_pair_dist(distances, id1, id2):
    try:
        return distances[(id1, id2)]
    except KeyError:
        return distances[(id2, id1)]


def get_silhouette(clusters, distances):
    """
    Calculate and save the silhouettue width of each cluster and returns
    the average silhouette width of all clusters
    """
    for cluster in clusters:
        len_c = len(cluster)
        for point in cluster.points:
            point_atot = sum(get_pair_dist(distances, point.id, p.id) 
                             for p in cluster.points if p is not point)
            if len_c != 1:
                a = point_atot / (len_c - 1)
                bs = []
                for other_c in clusters:
                    if other_c is cluster:
                        continue
                    point_btot = sum(get_pair_dist(distances, point.id, p.id) 
                                     for p in other_c.points)
                    bs.append(point_btot / len(other_c))
                b = min(bs)
                point.silhouette = (b - a) / max(a, b)
            else:
                point.silhouette = 0
        cluster.silhouette = sum(p.silhouette for p in cluster.points) / len_c
    all_sils = [p.silhouette for p in 
                itertools.chain(*(c.points for c in clusters))]
    return sum(all_sils) / len(all_sils)


def do_clustering(pdiff, parse_cat):
    k = pdiff.gopts.k
    points = get_points(pdiff, parse_cat.used_items)
    len_points = len(points)
    if len_points <= 1:
        return None
    if pdiff.gopts.debug:
        msg = "Clustering {0} items from {1}"
        print msg.format(parse_cat.num_used_items, parse_cat.title)
    if len_points <= k:
        if len_points == 2:
            k = 2
        else:
            k = len_points - 1
        if pdiff.gopts.debug:
            print "Max k changed to {0}".format(k)
    if pdiff.gopts.debug:
        print "Calculating distances between points..."
    dists = get_all_distances(points)
    if pdiff.gopts.forcek:
        # just do clustering for k
        clusters, iterations = kmeans(points, k)
        sil = get_silhouette(clusters, dists)
    else:
        # select best number of cluster from up to k
        sil = -2
        for this_k in range(2, k + 1):
            this_cls, iterations = kmeans(copy.deepcopy(points), this_k)
            this_sil = get_silhouette(this_cls, dists)
            if this_sil > sil:
                sil = this_sil
                clusters = this_cls
                chosen_k = this_k
            if pdiff.gopts.debug:
                msg = "k = {0}, silhouette of {1:.3f}, with {2} iteration(s)"
                print msg.format(this_k, this_sil, iterations)
    if pdiff.gopts.debug:
        print "Best k = {0}".format(chosen_k)
        print "Found {0} clusters\n".format(len(clusters))
    return Results(sil, clusters)
