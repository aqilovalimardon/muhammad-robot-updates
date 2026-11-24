shader_type canvas_item;
render_mode unshaded;

uniform vec2 face_center;
uniform vec2 chest_center;

void fragment() {
    // The owned window can overlap its parent on a tight turn. Keep the face and chest clear.
    vec2 pixel = SCREEN_UV / SCREEN_PIXEL_SIZE;
    float face = length((pixel-face_center) / vec2(43.0, 39.0));
    float chest = length((pixel-chest_center) / vec2(37.0, 40.0));
    COLOR.a *= smoothstep(0.92, 1.15, min(face, chest));
}
