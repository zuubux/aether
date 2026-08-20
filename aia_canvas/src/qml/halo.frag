#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float width;
    float height;
    float time;
    vec4 haloColor;
} ubuf;

float hash(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

float noise(vec2 x) {
    vec2 p = floor(x);
    vec2 f = fract(x);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash(p);
    float b = hash(p + vec2(1.0, 0.0));
    float c = hash(p + vec2(0.0, 1.0));
    float d = hash(p + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float fbm(vec2 p) {
    float f = 0.0;
    float w = 0.5;
    for(int i = 0; i < 4; i++) {
        f += w * noise(p);
        p *= 2.0;
        w *= 0.5;
    }
    return f;
}

// SDF for a pill capsule shape
float sdPill(vec2 p, float w, float h) {
    // The pill extends from -w/2 to w/2, and -h/2 to h/2.
    // The radius is the minimum of w or h.
    float r = min(w, h) * 0.5;
    // Internal box dimensions
    vec2 b = vec2(max(w * 0.5 - r, 0.0), max(h * 0.5 - r, 0.0));
    vec2 d = abs(p) - b;
    return min(max(d.x, d.y), 0.0) + length(max(d, 0.0)) - r;
}

void main() {
    // Convert 0..1 qt_TexCoord0 to physical coordinates centered at 0,0
    vec2 p = (qt_TexCoord0 - 0.5) * vec2(ubuf.width, ubuf.height);
    
    // Normalized distance from center (0.0 at center, 1.0 at edges)
    float dist = length(qt_TexCoord0 - 0.5) * 2.0;
    
    // Solid volumetric core density peaking at the centroid and decaying outward
    float coreDensity = max(0.0, 1.0 - dist);
    
    float uRadius = min(ubuf.width, ubuf.height) * 0.5;
    
    // Volumetric fog noise
    vec2 noiseUv = (p / uRadius) * 1.5 + vec2(ubuf.time * 0.2, ubuf.time * 0.1);
    float n = fbm(noiseUv);
    
    // Modulate core density with fbm noise pass
    float density = coreDensity * n;
    
    // Luminosity boosts the center and uses the base color
    float lumi = coreDensity * 1.5;
    vec4 finalColor = ubuf.haloColor * lumi;
    
    // Unconditional radial alpha falloff based on normalized UV distance from quad center
    vec2 uv = qt_TexCoord0;
    float r = length(uv - 0.5) * 2.0;
    float vignette = 1.0 - smoothstep(0.0, 1.0, r);
    
    // Multiply final color by density, vignette, and global opacity
    fragColor = finalColor * density * vignette * ubuf.qt_Opacity;
}
