#!/usr/bin/python2.4

import re
import sys
import clusterfiltering

#required_lines= int(sys.argv[2])
el= re.compile('.*:(\d+) NODE_KIND.*')
def vector_linecount( vector ):
    m= el.match(vector)
    if m == None:
        return -1
    return int( m.group(1) )

#NOTE: filenames can contain spaces...
range_r= re.compile('.*FILE (.*) LINE:(\d+):(\d+) NODE_KIND.*')
def vector_linerange( vector ):
    m= range_r.match(vector)
    if m == None:
        return (None,-1,-1,None)
    loc = clusterfiltering.getlocations( m.group(1) )
    return ( m.group(1), int(m.group(2)), int(m.group(2))+int(m.group(3))-1, loc )


vc= re.compile('.*nVARs:(\d+) NUM_NODE.*')
def vector_varcount( vector ):
    m= vc.match(vector)
    if m == None:
        return -1
    return int( m.group(1) )

    
def has_enough_lines( cluster ):
    for vector in cluster:
        lines= vector_linecount( vector )
        if lines >= required_lines:
            return True
    return False

def line_diff_big( cluster ):
    maxl= reduce( lambda x,y: max(x,y), map( vector_linecount, cluster ))
    minl= reduce( lambda x,y: min(x,y), map( vector_linecount, cluster ))
    if maxl>minl+5:
        return False
    return True

def count_duplicates( l, i ):
    n= 0
    for item in l:
        if i==item:
            n+=1
    return n

def only_one_diff( cluster ):
    counts= map( vector_varcount, cluster )
    counts.sort()
    if counts[-1] - counts[0] > 2:
        return False
    front= count_duplicates(counts,counts[0])
    back= count_duplicates(counts,counts[-1])
    if front < len(counts) and front >= len(counts)-2:
        return True
    if back < len(counts) and back >= len(counts)-2:
        return True
    return False

def remove_staggered( cluster ):
    rs= map( vector_linerange, cluster )
    keep= map( lambda x: True, cluster )
    for i in range(len(rs)-1):
        for j in range(i+1,len(rs)):
            if rs[j][2] == rs[i][2] and rs[j][0] < rs[i][1] \
                    and rs[j][0] > rs[i][0] and rs[j][1] > rs[i][1] \
                    and (rs[i][1]-rs[j][0])*2 >= rs[i][1]-rs[i][0] \
                    and (rs[j][1]-rs[i][1])*2 <= rs[i][1]-rs[i][0]:
                keep[j]= False
    newlist= []
    for i in range(len(cluster)):
        if keep[i]:
            newlist.append(cluster[i])
    return newlist

def remove_overlaping( cluster ):
    rs= map( vector_linerange, cluster )
    keep= map( lambda x: True, cluster )
    for i in range(1, len(rs)):
        for j in range(i):
            if keep[j]== True and clusterfiltering.is_loc_overlapping(rs[i][3], rs[j][3]):
               keep[i] = False
               break
    newlist= []
    for i in range(len(cluster)):
        if keep[i]:
            newlist.append(cluster[i])
    return newlist

def cluster_lineranges( cluster ):
    size= len(cluster)
    rsl=([], [], size)
    for i in range(size):
        m= range_r.match(cluster[i])
        if m != None:
            rsl[0].append( (int(m.group(2)), int(m.group(2))+int(m.group(3))-1) )
            rsl[1].append( m.group(1) )
    return rsl

def remove_contained_across_clusters ( clusters ):
#should have no effect on cd_coverage: compare each range and filename (luckily sorted by filenames)
#too slow (from seconds to minutes)...range tree will be better, but it's worthwhile for bug filtering because it reduces the re-parsing time about 1/3 (several minutes)
    rs= map( cluster_lineranges, clusters )
    keep= map( lambda x: True, clusters )
    for i in range(len(rs)):
        for j in range(len(rs)):
            if not keep[i] or not keep[j] or i == j:
                continue
            if rs[j][2] == rs[i][2] and len(rs[j][1]) == len(rs[i][1]):
                filematch= True
                for fn in range(len(rs[i][1])):
                    if rs[i][0][fn][0] >= rs[j][0][fn][0] and rs[i][0][fn][1] <= rs[j][0][fn][1] \
                            and rs[j][1][fn] == rs[i][1][fn]:
                        continue
                    else:
                        filematch= False
                        break
                if filematch:
                    keep[i]= False
    newlist= []
    for i in range(len(clusters)):
        if keep[i]:
            newlist.append(clusters[i])
    return newlist

def remove_contained( cluster ):
    rs= map( vector_linerange, cluster )
    keep= map( lambda x: True, cluster )
    for i in range(len(rs)):
        for j in range(len(rs)):
            if not keep[i] or i == j or not keep[j]:
                continue
            if rs[j][2] == rs[i][2] \
                    and rs[i][0] >= rs[j][0] and rs[i][1] <= rs[j][1]:
                keep[i]= False
    newlist= []
    for i in range(len(cluster)):
        if keep[i]:
            newlist.append(cluster[i])
    return newlist

def not_empty( cluster ):
    if len(cluster) <= 1:
        return False
    return True

def cmp_linecount( c1, c2 ):
    c1l= map( vector_linecount, c1 )
    c2l= map( vector_linecount, c2 )
    m1= reduce( max, c1l )
    m2= reduce( max, c2l )
    if m1 > m2: return -1
    if m1 == m2: return 0
    return 1

def readclusters( file ):
#    print file
    f= open(file,'r')
    clusters= []
    cluster= []
    for line in f.readlines():
        if line == '\n' or line == '':
            if len(cluster) > 0:
                clusters.append(cluster)
                cluster=[]
            continue
        cluster.append(line)
    f.close()
    if len(cluster) > 0:
        clusters.append(cluster)
#    clusters= clusters[1:]
    return clusters

def clusterstat( clusters ):
    sizes = []
    for c in clusters:
        sizes.append((len(c),c))
    sizes.sort()
    for s in sizes:
        print s[0]
        for v in s[1]:
            print v,
        print


def main():
    if len(sys.argv) != 2:
       print "Usage: ", sys.argv[0], " <orig clone reports>"
       sys.exit(1)

    clusters= readclusters( sys.argv[1] )
    clusterstat(clusters)
    sys.exit(0)

    clusters= map( remove_overlaping, clusters )
    clusters= filter( not_empty, clusters )
    clusters.sort( cmp_linecount )

    #print len(clusters), 'clusters'
    #print
    for cluster in clusters:
        for line in cluster:
            print line,
        print


if __name__ == '__main__':
   main()

