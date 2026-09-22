BEGIN { print "node_id,lat,lon" }
/"type": "node"/ { intype=1; id=""; lat=""; lon=""; next }
intype && /"id":/ { match($0, /[0-9]+/); id = substr($0, RSTART, RLENGTH); next }
intype && /"lat":/ { match($0, /-?[0-9.]+/); lat = substr($0, RSTART, RLENGTH); next }
intype && /"lon":/ { match($0, /-?[0-9.]+/); lon = substr($0, RSTART, RLENGTH); if (id != "" && lat != "") { print id "," lat "," lon }; intype=0; next }
