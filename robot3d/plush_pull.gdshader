shader_type spatial;
render_mode cull_disabled;

uniform vec4 cream : source_color;
uniform vec3 rest_scale = vec3(1.0);
uniform vec3 rest_center = vec3(0.0);
uniform bool strands = false;
uniform vec3 anchor = vec3(0.0);
uniform vec3 extension = vec3(0.0);

void vertex() {
    // Skin and fibers share the same rest-space patch. Roots follow the skin,
    // while the tips follow the fingertips farther out.
    vec3 relative = VERTEX * rest_scale + rest_center - anchor;
    float weight = 1.0 - smoothstep(0.035, 0.42, length(relative));
    float tip = strands ? UV.x : 0.0;
    VERTEX += extension * weight * mix(0.43, 1.12, tip) / rest_scale;
}

void fragment() {
    ALBEDO = cream.rgb;
    ROUGHNESS = 0.96;
}
