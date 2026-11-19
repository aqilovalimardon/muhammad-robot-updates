extends RefCounted
## Tracks a single pinch of coat on the head or torso. Only the selected
## materials receive per-frame updates, and hit testing only runs on press.
const COAT = preload("res://plush_pull.gdshader")
const MAX_EXTENSION = 0.53
const DEAD_ZONE = 5.0

class Patch:
    var skin: MeshInstance3D
    var fibers: MeshInstance3D
    var roots: PackedVector3Array
    var skin_mat: ShaderMaterial
    var fur_mat: ShaderMaterial

var patches: Array[Patch] = []
var occluders: Array[MeshInstance3D] = []
var selected: Patch
var armed := false
var pulling := false
var drag_origin := Vector2.ZERO
var out_direction := Vector2.ZERO
var target := Vector3.ZERO
var displacement := Vector3.ZERO
var velocity := Vector3.ZERO

func _material(tint: Color, scale: Vector3, center: Vector3, strands: bool) -> ShaderMaterial:
    var material := ShaderMaterial.new()
    material.shader = COAT
    material.set_shader_parameter("cream", tint)
    material.set_shader_parameter("rest_scale", scale)
    material.set_shader_parameter("rest_center", center)
    material.set_shader_parameter("strands", strands)
    return material

func add_patch(skin: MeshInstance3D, coat: MeshInstance3D, roots: PackedVector3Array,
        skin_color: Color, hair_color: Color) -> void:
    var patch := Patch.new()
    patch.skin = skin
    patch.fibers = coat
    patch.roots = roots
    patch.skin_mat = _material(skin_color, skin.scale, skin.position, false)
    patch.fur_mat = _material(hair_color, Vector3.ONE, Vector3.ZERO, true)
    skin.material_override = patch.skin_mat
    coat.material_override = patch.fur_mat
    # Allow Godot to draw a stretched edge outside the undeformed bounding box.
    coat.extra_cull_margin = MAX_EXTENSION
    skin.extra_cull_margin = MAX_EXTENSION
    patches.append(patch)
    occluders.append(skin)

func _visible_depth(origin: Vector3, direction: Vector3) -> float:
    var nearest := INF
    for surface in occluders:
        var inverse := surface.global_transform.affine_inverse()
        var o := inverse * origin
        var d := inverse.basis * direction
        var a := d.length_squared()
        var b := o.dot(d)
        var disc := b * b - a * (o.length_squared() - 1.0)
        if disc >= 0.0:
            var depth := (-b - sqrt(disc)) / a
            if depth >= 0.0:
                nearest = minf(nearest, depth)
    return nearest

func arm(camera: Camera3D, point: Vector2, pointer: Vector2) -> void:
    reset()
    var origin := camera.project_ray_origin(point)
    var ray := camera.project_ray_normal(point)
    var visible_depth := _visible_depth(origin, ray)
    var best := 36.0 # within six desktop pixels of an actual visible tuft
    var anchor := Vector3.ZERO
    for patch in patches:
        var coat_transform := patch.fibers.global_transform
        for root in patch.roots:
            var world := coat_transform * root
            var depth := (world - origin).dot(ray)
            if depth > visible_depth + 0.10:
                continue
            var screen := camera.unproject_position(world)
            var distance := point.distance_squared_to(screen)
            if distance < best:
                best = distance
                selected = patch
                anchor = root
                out_direction = (screen - camera.unproject_position(patch.skin.global_position)).normalized()
    if selected != null:
        drag_origin = pointer
        armed = true
        for material in [selected.skin_mat, selected.fur_mat]:
            material.set_shader_parameter("anchor", anchor)

func move(camera: Camera3D, pointer: Vector2) -> bool:
    if not armed:
        return false
    var delta := pointer - drag_origin
    if not pulling:
        if delta.length() < DEAD_ZONE:
            return true
        if delta.normalized().dot(out_direction) < 0.32:
            reset()
            return false
        pulling = true
    var depth := camera.global_position.distance_to(selected.skin.global_position)
    # The orthographic camera maps desktop pixels to the coat's 3D coordinates.
    var world_delta := camera.project_position(delta, depth) - camera.project_position(Vector2.ZERO, depth)
    target = (selected.fibers.global_transform.basis.inverse() * world_delta).limit_length(MAX_EXTENSION)
    return true

func release() -> void:
    armed = false
    pulling = false
    target = Vector3.ZERO

func advance(delta: float) -> void:
    if selected == null:
        return
    var remaining := minf(delta, 0.12)
    while remaining > 0.0:
        var step := minf(remaining, 1.0 / 120.0)
        remaining -= step
        var stiffness := 185.0 if pulling else 100.0
        var damping := 23.0 if pulling else 12.0
        velocity += ((target - displacement) * stiffness - velocity * damping) * step
        displacement = (displacement + velocity * step).limit_length(MAX_EXTENSION)
    _apply()
    if not armed and displacement.length_squared() + velocity.length_squared() < 0.000005:
        reset()

func _apply() -> void:
    selected.skin_mat.set_shader_parameter("extension", displacement)
    selected.fur_mat.set_shader_parameter("extension", displacement)

func reset() -> void:
    release()
    velocity = Vector3.ZERO
    displacement = Vector3.ZERO
    if selected != null:
        _apply()
    selected = null
