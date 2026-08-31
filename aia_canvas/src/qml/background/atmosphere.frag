#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float width;
    float height;
    float cameraX;
    float cameraY;
    float parallaxFactor;
    float _pad;
    vec4 centerColor;
    vec4 midColor;
    vec4 outerColor;
} ubuf;

float pseudoNoise(vec2 co) {
    return fract(sin(dot(co, vec2(12.9898, 78.233))) * 43758.5453123) - 0.5;
}

void main() {
    vec2 uv = qt_TexCoord0;
    
    // Parallax shifted center in normalized UV coordinates [0.0, 1.0]
    vec2 viewportSize = vec2(max(1.0, ubuf.width), max(1.0, ubuf.height));
    vec2 offsetUV = (vec2(ubuf.cameraX, ubuf.cameraY) * ubuf.parallaxFactor) / viewportSize;
    vec2 centerUV = vec2(0.5, 0.5) + offsetUV;
    
    // Normalized distance vector from gradient center
    vec2 d = (uv - centerUV) * 2.0;
    float dist = length(d);
    
    // 3-stop radial gradient interpolation:
    // [0.0 - 0.55]: centerColor (#07111E) -> midColor (#030712)
    // [0.55 - 1.0]: midColor (#030712) -> outerColor (#000000)
    // [> 1.0]:      outerColor (#000000)
    vec4 color;
    if (dist <= 0.55) {
        float t = dist / 0.55;
        t = smoothstep(0.0, 1.0, t);
        color = mix(ubuf.centerColor, ubuf.midColor, t);
    } else if (dist <= 1.0) {
        float t = (dist - 0.55) / 0.45;
        t = smoothstep(0.0, 1.0, t);
        color = mix(ubuf.midColor, ubuf.outerColor, t);
    } else {
        color = ubuf.outerColor;
    }
    
    // Subtle micro-dithering pass (1/255 scale) to eliminate 8-bit dark color banding
    float noise = pseudoNoise(gl_FragCoord.xy) * (1.0 / 255.0);
    vec3 ditheredRgb = clamp(color.rgb + vec3(noise), 0.0, 1.0);
    
    fragColor = vec4(ditheredRgb, color.a) * ubuf.qt_Opacity;
}
