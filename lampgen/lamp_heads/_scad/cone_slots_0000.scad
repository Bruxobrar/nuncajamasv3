
$fn = 80;

module head_shell(shape, d_out, h_out) {
    if (shape == "cylinder") {
        cylinder(h=h_out, d=d_out);
    }
    else if (shape == "cone") {
        cylinder(h=h_out, d1=d_out, d2=d_out*0.6);
    }
    else if (shape == "dome") {
        union() {
            cylinder(h=h_out*0.7, d=d_out);
            translate([0,0,h_out*0.7])
                sphere(d=d_out);
        }
    }
}

module pattern_slots(d_out,h_out,count,depth,width) {
    for(i=[0:count-1]) {
        rotate([0,0,i*(360/count)])
        translate([d_out/2-depth/2,0,h_out/2])
        cube([depth,width,h_out],center=true);
    }
}

module pattern_holes(d_out,h_out,count,d) {
    for(i=[0:count-1]) {
        rotate([0,0,i*(360/count)])
        translate([d_out/2-2,0,h_out*0.5])
        rotate([0,90,0])
        cylinder(h=6,d=d,center=true);
    }
}

module make_head() {

    difference() {

        head_shell("cone", 109.25, 142.32);

        if("slots"=="slots")
            pattern_slots(109.25,142.32,11,4,2);

        if("slots"=="holes")
            pattern_holes(109.25,142.32,11,3);

        translate([0,0,0])
            cylinder(h=142.32,d=109.25-2*2.0);
    }
}

make_head();
