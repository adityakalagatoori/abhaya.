[out:json][timeout:120];
(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|residential|unclassified)$"](26.80,75.70,27.00,75.95);
);
out body;
>;
out skel qt;
