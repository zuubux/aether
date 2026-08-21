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

vec2 hash22(vec2 p) {
    p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
    return fract(sin(p) * 43758.5453);
}

float voronoi_edge(vec2 x) {
    vec2 n = floor(x);
    vec2 f = fract(x);
    
    vec2 mr;
    vec2 mg;
    
    float md = 8.0;
    for (int j = -1; j <= 1; j++) {
        for (int i = -1; i <= 1; i++) {
            vec2 g = vec2(float(i), float(j));
            vec2 o = hash22(n + g);
            o = 0.5 + 0.5 * sin(ubuf.time * 0.2 + 6.2831 * o);
            vec2 r = g + o - f;
            float d = dot(r, r);
            if (d < md) {
                md = d;
                mr = r;
                mg = g;
            }
        }
    }
    
    md = 8.0;
    for (int j = -2; j <= 2; j++) {
        for (int i = -2; i <= 2; i++) {
            vec2 g = mg + vec2(float(i), float(j));
            vec2 o = hash22(n + g);
            o = 0.5 + 0.5 * sin(ubuf.time * 0.2 + 6.2831 * o);
            vec2 r = g + o - f;
            
            if (dot(mr - r, mr - r) > 0.00001) {
                float d = dot(0.5 * (mr + r), normalize(r - mr));
                md = min(md, d);
            }
        }
    }
    return md;
}

void main() {
    vec2 uv = qt_TexCoord0;
    vec2 p = uv - 0.5;
    
    float aspect = ubuf.width / max(1.0, ubuf.height);
    vec2 p_scaled = p * vec2(aspect, 1.0);
    
    float d = voronoi_edge(p_scaled * 2.28 + vec2(ubuf.time * 0.05));
    
    float lineThickness = 0.008; 
    float web = 1.0 - smoothstep(0.0, lineThickness, d);
    
    vec3 desaturatedColor = mix(ubuf.haloColor.rgb, vec3(dot(ubuf.haloColor.rgb, vec3(0.299, 0.587, 0.114))), 0.6);
    
    float webOpacity = mix(0.05, 0.15, web);
    
    float dist = length(p) * 2.0;
    float edgeMask = smoothstep(1.0, 0.0, dist);
    
    vec4 finalColor = vec4(desaturatedColor * web * edgeMask, web * webOpacity * edgeMask);
    
    fragColor = finalColor * ubuf.qt_Opacity;
}
