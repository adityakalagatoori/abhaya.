BEGIN {
  print "way_id,node_id" > "way_nodes.csv"
  print "way_id,highway,name,oneway" > "way_tags.csv"
}
/"type": "way"/ { inway=1; innodes=0; intags=0; wid=""; hw=""; nm=""; ow=""; next }
inway && /"id":/ && !innodes && !intags { match($0, /[0-9]+/); wid = substr($0, RSTART, RLENGTH); next }
inway && /"nodes": \[/ { innodes=1; next }
innodes && /\]/ { innodes=0; next }
innodes { gsub(/[ ,]/, ""); if ($0 != "") print wid "," $0 > "way_nodes.csv"; next }
inway && /"tags": \{/ { intags=1; next }
intags && /^\s*\}/ {
  print wid "," hw "," nm "," ow > "way_tags.csv"
  intags=0; inway=0; next
}
intags && /"highway":/ { match($0, /"highway": "[^"]*"/); s=substr($0,RSTART,RLENGTH); sub(/"highway": "/,"",s); sub(/"$/,"",s); hw=s; next }
intags && /"name":/ { match($0, /"name": "[^"]*"/); s=substr($0,RSTART,RLENGTH); sub(/"name": "/,"",s); sub(/"$/,"",s); gsub(/,/,";",s); nm=s; next }
intags && /"oneway":/ { match($0, /"oneway": "[^"]*"/); s=substr($0,RSTART,RLENGTH); sub(/"oneway": "/,"",s); sub(/"$/,"",s); ow=s; next }
