BEGIN {
  FS=","
  # load nodes
  while ((getline line < NODES_FILE) > 0) {
    n++
    if (n==1) continue
    split(line, a, ",")
    nlat[a[1]]=a[2]; nlon[a[1]]=a[3]
  }
  # load tags
  while ((getline line < TAGS_FILE) > 0) {
    t++
    if (t==1) continue
    split(line, a, ",")
    thw[a[1]]=a[2]; tnm[a[1]]=a[3]; tow[a[1]]=a[4]
  }
  print "way_id,from_node,to_node,highway,name,oneway" > EDGES_OUT
  print "{\"type\":\"FeatureCollection\",\"features\":[" > GEOJSON_OUT
  first=1
}
FNR==1 { curway=""; delete coords; ccount=0 }
FNR>1 {
  split($0, a, ",")
  wid=a[1]; nid=a[2]
  if (wid != curway) {
    if (curway != "" && ccount > 1) { flush_geojson(curway) }
    curway=wid; ccount=0
  }
  if (nid in nlat) {
    ccount++
    coords[ccount]=nlon[nid] "," nlat[nid]
    if (ccount>1) {
      print wid "," prevnode "," nid "," thw[wid] "," tnm[wid] "," tow[wid] > EDGES_OUT
    }
    prevnode=nid
  }
}
END {
  if (curway != "" && ccount > 1) { flush_geojson(curway) }
  print "]}" > GEOJSON_OUT
}
function flush_geojson(wid,   cstr, i, props, nmv, hwv, owv) {
  cstr=""
  for (i=1;i<=ccount;i++) {
    cstr = cstr (i>1?",":"") "[" coords[i] "]"
  }
  hwv=thw[wid]; nmv=tnm[wid]; owv=tow[wid]
  gsub(/"/,"\\\"",nmv)
  props = "{\"highway\":\"" hwv "\",\"name\":\"" nmv "\",\"oneway\":\"" owv "\",\"osm_id\":" wid "}"
  if (!first) print "," > GEOJSON_OUT
  first=0
  print "{\"type\":\"Feature\",\"geometry\":{\"type\":\"LineString\",\"coordinates\":[" cstr "]},\"properties\":" props "}" > GEOJSON_OUT
}
