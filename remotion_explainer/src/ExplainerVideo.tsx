import React from "react";
import {
  AbsoluteFill,
  Sequence,
  spring,
  interpolate,
  useCurrentFrame,
  useVideoConfig
} from "remotion";

export interface SceneItem {
  scene_number: number;
  section_badge: string;
  headline: string;
  bullet_points: string[];
  highlight_box: string;
  narration_text?: string;
  motion_style?: string;
  pointer_label?: string;
  image_url?: string;
  image2_url?: string;
  icon_type: string;
  theme_name: string;
  durationInFrames: number;
}

export interface ExplainerProps {
  topicTitle: string;
  targetAudience: string;
  scenes: SceneItem[];
}

const THEMES: Record<
  string,
  { bg1: string; bg2: string; card: string; accent: string; soft: string; glow: string }
> = {
  emerald_gold: {
    bg1: "#073429",
    bg2: "#02130f",
    card: "rgba(10, 56, 44, 0.92)",
    accent: "#ffd426",
    soft: "#fff4c2",
    glow: "rgba(255, 212, 38, 0.25)"
  },
  royal_teal: {
    bg1: "#083747",
    bg2: "#03151e",
    card: "rgba(12, 64, 82, 0.92)",
    accent: "#3cf0de",
    soft: "#d4fffb",
    glow: "rgba(60, 240, 222, 0.25)"
  },
  midnight_amber: {
    bg1: "#142446",
    bg2: "#060c1b",
    card: "rgba(24, 44, 84, 0.92)",
    accent: "#ffbe2e",
    soft: "#ffefba",
    glow: "rgba(255, 190, 46, 0.25)"
  },
  deep_ocean: {
    bg1: "#0b2e52",
    bg2: "#041122",
    card: "rgba(16, 56, 98, 0.92)",
    accent: "#6ad4ff",
    soft: "#dbf4ff",
    glow: "rgba(106, 212, 255, 0.25)"
  },
  warm_emerald: {
    bg1: "#113a2d",
    bg2: "#051711",
    card: "rgba(20, 70, 54, 0.92)",
    accent: "#f8dc5c",
    soft: "#fff9d6",
    glow: "rgba(248, 220, 92, 0.25)"
  }
};

const STYLE_LABELS: Record<string, string> = {
  "isometrik-dibongkar": "3D ISOMETRIK",
  "sejarah-3d": "SEJARAH 3D SINEMATIK",
  "tubuh-anime": "VISUAL ANIME",
  "dunia-2d": "DUNIA 2D BERTEKSTUR",
  "kartun-cel": "KARTUN CEL CERAH",
  "peta-relief": "PETA RELIEF",
  "promo-produk": "SPOTLIGHT KINETIK"
};

/**
 * Lapisan Visual Khas 7 Gaya Motion Format v2 (E:\Motion Course\motion-format)
 */
const MotionStyleBackdrop: React.FC<{
  styleId: string;
  accent: string;
  soft: string;
  frame: number;
}> = ({ styleId, accent, soft, frame }) => {
  if (styleId === "isometrik-dibongkar") {
    return (
      <svg
        width="1920"
        height="1080"
        viewBox="0 0 1920 1080"
        style={{ position: "absolute", inset: 0, pointerEvents: "none", opacity: 0.22 }}
      >
        {/* Isometric Blueprint Grid & Technical Crosshairs */}
        {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
          <React.Fragment key={i}>
            <line
              x1={0}
              y1={i * 160 + ((frame * 1.2) % 160)}
              x2={1920}
              y2={i * 160 + 280 + ((frame * 1.2) % 160)}
              stroke={accent}
              strokeWidth="1"
              strokeDasharray="10 8"
            />
            <line
              x1={i * 260}
              y1={0}
              x2={i * 260 - 240}
              y2={1080}
              stroke={accent}
              strokeWidth="1"
              strokeDasharray="6 10"
            />
          </React.Fragment>
        ))}
        <g transform={`translate(1540, 520) rotate(${frame * 0.6})`}>
          <circle cx="0" cy="0" r="290" stroke={accent} strokeWidth="2" fill="none" strokeDasharray="14 8" />
          <circle cx="0" cy="0" r="230" stroke={soft} strokeWidth="1.5" fill="none" />
          <line x1="-320" y1="0" x2="320" y2="0" stroke={accent} strokeWidth="1.5" />
          <line x1="0" y1="-320" x2="0" y2="320" stroke={accent} strokeWidth="1.5" />
        </g>
      </svg>
    );
  }

  if (styleId === "sejarah-3d") {
    return (
      <svg
        width="1920"
        height="1080"
        viewBox="0 0 1920 1080"
        style={{ position: "absolute", inset: 0, pointerEvents: "none", opacity: 0.24 }}
      >
        {/* Volumetric Golden God-Rays & Classical Arch Silhouette */}
        <polygon
          points={`180,0 520,0 ${920 + Math.sin(frame * 0.04) * 60},1080 340,1080`}
          fill={accent}
          opacity="0.16"
        />
        <polygon
          points={`780,0 1120,0 ${1580 + Math.cos(frame * 0.04) * 60},1080 980,1080`}
          fill={soft}
          opacity="0.12"
        />
        <path
          d="M 1220 980 L 1220 420 Q 1545 140 1870 420 L 1870 980"
          stroke={accent}
          strokeWidth="3"
          fill="none"
          strokeDasharray="12 6"
        />
      </svg>
    );
  }

  if (styleId === "peta-relief") {
    const dashOffset = -(frame * 3.5);
    const pinProgress = (frame % 120) / 120;
    const pinX = 1280 + pinProgress * 460;
    const pinY = 660 - Math.sin(pinProgress * Math.PI) * 220;
    return (
      <svg
        width="1920"
        height="1080"
        viewBox="0 0 1920 1080"
        style={{ position: "absolute", inset: 0, pointerEvents: "none", opacity: 0.25 }}
      >
        {/* Topographic Contour Lines & Animated Route Path */}
        {[120, 190, 260, 330, 400].map((r, idx) => (
          <ellipse
            key={idx}
            cx={1520}
            cy={520}
            rx={r * 1.35}
            ry={r * 0.85}
            stroke={accent}
            strokeWidth="1.8"
            fill="none"
            strokeDasharray={idx % 2 === 0 ? "none" : "10 6"}
            transform={`rotate(${idx * 12 + frame * 0.15} 1520 520)`}
          />
        ))}
        <path
          d="M 1180 680 Q 1480 280 1820 580"
          stroke={soft}
          strokeWidth="4"
          fill="none"
          strokeDasharray="14 10"
          strokeDashoffset={dashOffset}
        />
        <circle cx={pinX} cy={pinY} r="14" fill={accent} />
        <circle cx={pinX} cy={pinY} r="28" stroke={accent} strokeWidth="2.5" fill="none" />
      </svg>
    );
  }

  if (styleId === "tubuh-anime") {
    return (
      <svg
        width="1920"
        height="1080"
        viewBox="0 0 1920 1080"
        style={{ position: "absolute", inset: 0, pointerEvents: "none", opacity: 0.24 }}
      >
        {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => {
          const cx = (i * 250 + Math.sin(frame * 0.05 + i) * 65) % 1920;
          const cy = 980 - ((frame * (2.2 + (i % 3) * 0.6) + i * 140) % 960);
          const r = 18 + (i % 4) * 12;
          return (
            <g key={i}>
              <circle cx={cx} cy={cy} r={r} stroke={accent} strokeWidth="2.5" fill={accent} fillOpacity="0.15" />
              <circle cx={cx - r * 0.3} cy={cy - r * 0.3} r={r * 0.28} fill={soft} fillOpacity="0.6" />
            </g>
          );
        })}
      </svg>
    );
  }

  if (styleId === "kartun-cel") {
    return (
      <svg
        width="1920"
        height="1080"
        viewBox="0 0 1920 1080"
        style={{ position: "absolute", inset: 0, pointerEvents: "none", opacity: 0.2 }}
      >
        {/* Cel-Shaded Pop Burst & Halftone Accents */}
        <g transform={`translate(1550, 520) rotate(${frame * 0.45})`}>
          {[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330].map((deg) => (
            <line
              key={deg}
              x1="0"
              y1="0"
              x2={Math.cos((deg * Math.PI) / 180) * 380}
              y2={Math.sin((deg * Math.PI) / 180) * 380}
              stroke={accent}
              strokeWidth="4"
              strokeDasharray="18 14"
            />
          ))}
        </g>
      </svg>
    );
  }

  return (
    <svg
      width="760"
      height="760"
      viewBox="0 0 200 200"
      style={{
        position: "absolute",
        right: -140,
        top: 120,
        opacity: 0.16,
        transform: `rotate(${frame * 0.35}deg) scale(${1 + Math.sin(frame * 0.03) * 0.06})`
      }}
    >
      <circle cx="100" cy="100" r="88" stroke={accent} strokeWidth="2" fill="none" strokeDasharray="8 6" />
      <circle cx="100" cy="100" r="68" stroke={accent} strokeWidth="1.5" fill="none" />
      <polygon points="100,15 185,100 100,185 15,100" stroke={accent} strokeWidth="1.5" fill="none" />
      <polygon points="40,40 160,40 160,160 40,160" stroke={accent} strokeWidth="1.5" fill="none" />
    </svg>
  );
};

const DynamicSvgIcon: React.FC<{
  iconType: string;
  accent: string;
  frame: number;
  topicTitle: string;
}> = ({ iconType, accent, frame, topicTitle }) => {
  const floatY = Math.sin(frame * 0.08) * 6;
  const pulse = 1 + Math.sin(frame * 0.1) * 0.05;
  const isPlaneTopic =
    topicTitle.toLowerCase().includes("pesawat") ||
    topicTitle.toLowerCase().includes("terbang") ||
    iconType.toLowerCase() === "plane";

  return (
    <div
      style={{
        width: 108,
        height: 108,
        borderRadius: 26,
        background: `radial-gradient(circle, ${accent}33 0%, rgba(4,20,16,0.92) 100%)`,
        border: `3.5px solid ${accent}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        transform: `translateY(${floatY}px) scale(${pulse})`,
        flexShrink: 0
      }}
    >
      {isPlaneTopic ? (
        <svg width="64" height="64" viewBox="0 0 24 24" fill={accent}>
          <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" />
        </svg>
      ) : iconType === "book" ? (
        <svg width="60" height="60" viewBox="0 0 24 24" fill={accent}>
          <path d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4z" />
        </svg>
      ) : iconType === "lightbulb" ? (
        <svg width="60" height="60" viewBox="0 0 24 24" fill={accent}>
          <path d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7z" />
        </svg>
      ) : iconType === "heart" ? (
        <svg width="60" height="60" viewBox="0 0 24 24" fill={accent}>
          <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
        </svg>
      ) : iconType === "shield" ? (
        <svg width="60" height="60" viewBox="0 0 24 24" fill={accent}>
          <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z" />
        </svg>
      ) : (
        <svg width="62" height="62" viewBox="0 0 24 24" fill={accent}>
          <path d="M12 2l2.4 7.4h7.6l-6.15 4.48 2.35 7.32-6.2-4.52-6.2 4.52 2.35-7.32L2 9.4h7.6z" />
        </svg>
      )}
    </div>
  );
};

const SceneCard: React.FC<{
  scene: SceneItem;
  totalScenes: number;
  topicTitle: string;
  targetAudience: string;
}> = ({ scene, totalScenes, topicTitle, targetAudience }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dur = Math.max(60, scene.durationInFrames || 300);
  const theme = THEMES[scene.theme_name] || THEMES.emerald_gold;
  const styleId = scene.motion_style || "isometrik-dibongkar";
  const styleBadgeText = STYLE_LABELS[styleId] || "MOTION FORMAT V2";

  // Dynamic entrance & exit animations
  const headerSpring = spring({ frame, fps, config: { damping: 12, stiffness: 120 } });
  const bulletStart1 = Math.floor(dur * 0.12);
  const bulletStart2 = Math.floor(dur * 0.32);
  const bulletStart3 = Math.floor(dur * 0.52);
  const boxStart = Math.floor(dur * 0.66);
  const pointerStart = Math.floor(dur * 0.18);

  const b1 = spring({ frame: frame - bulletStart1, fps, config: { damping: 12, stiffness: 110 } });
  const b2 = spring({ frame: frame - bulletStart2, fps, config: { damping: 12, stiffness: 110 } });
  const b3 = spring({ frame: frame - bulletStart3, fps, config: { damping: 12, stiffness: 110 } });
  const boxAnim = spring({ frame: frame - boxStart, fps, config: { damping: 11, stiffness: 105 } });
  const pointerAnim = spring({ frame: frame - pointerStart, fps, config: { damping: 12, stiffness: 115 } });

  const fadeOut = interpolate(frame, [dur - 8, dur], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp"
  });
  const overallProgress =
    ((scene.scene_number - 1 + Math.min(1, frame / dur)) / Math.max(1, totalScenes)) * 100;

  // Determine which bullet is currently spotlighted
  const activeBulletIdx =
    frame >= bulletStart3 ? 2 : frame >= bulletStart2 ? 1 : frame >= bulletStart1 ? 0 : -1;

  const points = (scene.bullet_points || []).slice(0, 3);
  const bulletSprings = [b1, b2, b3];
  const words = (scene.headline || topicTitle).split(" ");

  // Synchronized Word-by-Word Kinetic Subtitle (Motion Format `sub` engine)
  const narrationWords = (scene.narration_text || "").trim().split(/\s+/).filter(Boolean);
  const currentWordIndex =
    narrationWords.length > 0
      ? Math.min(
          narrationWords.length - 1,
          Math.max(0, Math.floor((frame / Math.max(1, dur * 0.94)) * narrationWords.length))
        )
      : -1;
  const subChunkSize = 9;
  const subChunkIndex = currentWordIndex >= 0 ? Math.floor(currentWordIndex / subChunkSize) : 0;
  const visibleSubWords = narrationWords.slice(
    subChunkIndex * subChunkSize,
    (subChunkIndex + 1) * subChunkSize
  );

  // Alternate subtle camera zoom/pan direction between even and odd scenes for rich visual variety
  const isEvenScene = scene.scene_number % 2 === 0;
  const imgScale = interpolate(
    frame,
    [0, dur],
    isEvenScene ? [1.2, 1.03] : [1.02, 1.22],
    { extrapolateRight: "clamp" }
  );
  const imgPanX = Math.sin(frame * 0.05) * (isEvenScene ? -12 : 12);
  const imgPanY = Math.cos(frame * 0.04) * 8;
  const pointerText = (scene.pointer_label || scene.headline || "VISUAL UTAMA").slice(0, 26);

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at 20% 20%, ${theme.bg1} 0%, ${theme.bg2} 100%)`,
        fontFamily: "'Segoe UI', 'DejaVu Sans', Arial, sans-serif",
        color: "#ffffff",
        padding: "42px 72px",
        opacity: fadeOut,
        overflow: "hidden"
      }}
    >
      {/* Blurred Topic Internet Photo Background Layer */}
      {scene.image_url && (
        <img
          src={scene.image_url}
          alt=""
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
            filter: "blur(20px) brightness(0.28)",
            opacity: 0.45,
            transform: `scale(${1.08 + Math.sin(frame * 0.02) * 0.04})`,
            pointerEvents: "none"
          }}
        />
      )}

      {/* 7 Motion Format v2 Dynamic Environment Layer */}
      <MotionStyleBackdrop styleId={styleId} accent={theme.accent} soft={theme.soft} frame={frame} />

      {/* Atmospheric Floating Depth Particles */}
      {[0, 1, 2, 3, 4, 5].map((pIdx) => {
        const px = (pIdx * 310 + frame * (1.2 + pIdx * 0.25)) % 1920;
        const py = 140 + ((pIdx * 170 + Math.sin(frame * 0.04 + pIdx) * 45) % 780);
        return (
          <div
            key={pIdx}
            style={{
              position: "absolute",
              left: px,
              top: py,
              width: 11 + (pIdx % 3) * 5,
              height: 11 + (pIdx % 3) * 5,
              borderRadius: "50%",
              background: theme.accent,
              opacity: 0.15,
              boxShadow: `0 0 16px ${theme.accent}`
            }}
          />
        );
      })}

      {/* Top Header Bar (Leaves x > 1680 clean for Islamic K1 Logo!) */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          maxWidth: 1640,
          transform: `translateY(${interpolate(headerSpring, [0, 1], [-40, 0])}px)`,
          opacity: headerSpring
        }}
      >
        <div
          style={{
            background: `linear-gradient(135deg, ${theme.accent} 0%, #ffffff 160%)`,
            color: "#041c15",
            fontWeight: 900,
            fontSize: 21,
            padding: "9px 24px",
            borderRadius: 999,
            letterSpacing: 1.1,
            boxShadow: `0 6px 20px ${theme.glow}`
          }}
        >
          SCENE {String(scene.scene_number).padStart(2, "0")} / {String(totalScenes).padStart(2, "0")}
        </div>

        <div
          style={{
            background: "rgba(255,255,255,0.10)",
            color: theme.soft,
            fontWeight: 800,
            fontSize: 19,
            padding: "9px 22px",
            borderRadius: 999,
            border: `2px solid ${theme.accent}77`
          }}
        >
          {targetAudience.toUpperCase().slice(0, 20)} • {scene.section_badge.toUpperCase().slice(0, 34)}
        </div>

        {/* Motion Format v2 Style Badge + Live Waveform */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 5,
            marginLeft: "auto",
            marginRight: 36,
            background: "rgba(0,0,0,0.42)",
            padding: "8px 18px",
            borderRadius: 999,
            border: `1.5px solid ${theme.accent}66`
          }}
        >
          {[0, 1, 2, 3, 4, 5].map((bar) => {
            const h = 9 + Math.abs(Math.sin(frame * 0.25 + bar * 0.9)) * 18;
            return (
              <div
                key={bar}
                style={{
                  width: 4,
                  height: h,
                  borderRadius: 4,
                  background: theme.accent
                }}
              />
            );
          })}
          <span style={{ marginLeft: 8, fontSize: 15, fontWeight: 900, color: theme.accent, letterSpacing: 0.8 }}>
            GAYA: {styleBadgeText}
          </span>
        </div>
      </div>

      {/* Main Kinetic Hero Section with Floating Icon & Word-by-Word Spring Headline */}
      <div
        style={{
          marginTop: 20,
          display: "flex",
          alignItems: "center",
          gap: 26,
          maxWidth: 1680
        }}
      >
        <DynamicSvgIcon
          iconType={scene.icon_type}
          accent={theme.accent}
          frame={frame}
          topicTitle={topicTitle}
        />

        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "11px" }}>
            {words.map((word, wIdx) => {
              const wSpring = spring({
                frame: frame - wIdx * 3,
                fps,
                config: { damping: 11, stiffness: 130 }
              });
              return (
                <span
                  key={wIdx}
                  style={{
                    display: "inline-block",
                    fontSize: 50,
                    fontWeight: 900,
                    lineHeight: 1.1,
                    color: wIdx % 2 === 1 ? theme.accent : "#ffffff",
                    textShadow: "0 8px 20px rgba(0,0,0,0.65)",
                    transform: `translateY(${interpolate(wSpring, [0, 1], [28, 0])}px) scale(${interpolate(wSpring, [0, 1], [0.85, 1])})`,
                    opacity: wSpring
                  }}
                >
                  {word}
                </span>
              );
            })}
          </div>
          <div
            style={{
              fontSize: 21,
              fontWeight: 800,
              color: theme.soft,
              letterSpacing: 1.0,
              opacity: 0.9
            }}
          >
            TOPIK: {topicTitle.toUpperCase()}
          </div>
        </div>
      </div>

      {/* Main Content Split: Alternating Multi-Layout (Cards <-> Dual Internet Image Showcase + Pointer Callout) */}
      <div
        style={{
          marginTop: 18,
          display: "flex",
          flexDirection: isEvenScene ? "row-reverse" : "row",
          alignItems: "stretch",
          gap: 28,
          maxWidth: 1776
        }}
      >
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            gap: 14,
            justifyContent: "center"
          }}
        >
          {points.map((pt, idx) => {
            const sp = bulletSprings[idx] ?? 1;
            const isCurrent = activeBulletIdx === idx;
            const pulseScale = isCurrent ? 1 + Math.sin(frame * 0.12) * 0.012 : 1;

            return (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 18,
                  background: isCurrent
                    ? `linear-gradient(90deg, ${theme.card} 0%, ${theme.accent}28 100%)`
                    : theme.card,
                  border: isCurrent ? `3.5px solid ${theme.accent}` : `2px solid rgba(255,255,255,0.22)`,
                  borderRadius: 20,
                  padding: "16px 22px",
                  transform: `translateX(${interpolate(sp, [0, 1], [-120, 0])}px) scale(${interpolate(sp, [0, 1], [0.9, pulseScale])})`,
                  opacity: sp
                }}
              >
                <div
                  style={{
                    minWidth: 54,
                    height: 54,
                    borderRadius: 15,
                    background: isCurrent ? theme.accent : "rgba(255,255,255,0.14)",
                    color: isCurrent ? "#041c15" : theme.accent,
                    border: `2px solid ${theme.accent}`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 26,
                    fontWeight: 900
                  }}
                >
                  0{idx + 1}
                </div>
                <div
                  style={{
                    fontSize: 28,
                    fontWeight: 800,
                    lineHeight: 1.24,
                    color: isCurrent ? "#ffffff" : theme.soft
                  }}
                >
                  {pt}
                </div>
              </div>
            );
          })}
        </div>

        {/* Dynamic Animated Visual Illustration Panel + Motion Format Pointer Callout (`label()`) */}
        {scene.image_url && (
          <div
            style={{
              width: 565,
              height: 400,
              borderRadius: styleId === "kartun-cel" ? 32 : 24,
              border: styleId === "kartun-cel" ? `5px solid #ffffff` : `4px solid ${theme.accent}`,
              boxShadow: `0 16px 36px rgba(0,0,0,0.55), 0 0 24px ${theme.glow}`,
              background: theme.card,
              overflow: "hidden",
              position: "relative",
              flexShrink: 0,
              transform: `translateY(${Math.sin(frame * 0.08) * 6}px) scale(${interpolate(headerSpring, [0, 1], [0.85, 1])})`,
              opacity: headerSpring
            }}
          >
            <img
              src={scene.image_url}
              alt={scene.headline}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                transform: `scale(${imgScale}) translate(${imgPanX}px, ${imgPanY}px)`
              }}
            />

            {/* Secondary Overlapping Topic Visual Card (Dual-Image Gallery) */}
            {scene.image2_url && (
              <div
                style={{
                  position: "absolute",
                  right: 14,
                  bottom: 52,
                  width: 225,
                  height: 152,
                  borderRadius: 16,
                  border: `3px solid #ffffff`,
                  boxShadow: "0 10px 24px rgba(0,0,0,0.75)",
                  overflow: "hidden",
                  transform: `rotate(${isEvenScene ? -3 : 3}deg) scale(${pointerAnim})`
                }}
              >
                <img
                  src={scene.image2_url}
                  alt=""
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    transform: `scale(${1.18 - (imgScale - 1.02) * 0.5})`
                  }}
                />
              </div>
            )}

            {/* Motion Format Pointer Callout (`label()` — glowing target dot + angled leader line + pill) */}
            <svg
              width="565"
              height="400"
              viewBox="0 0 565 400"
              style={{
                position: "absolute",
                inset: 0,
                pointerEvents: "none",
                opacity: pointerAnim
              }}
            >
              <circle
                cx={210 + Math.sin(frame * 0.06) * 8}
                cy={175 + Math.cos(frame * 0.06) * 6}
                r={7 + Math.sin(frame * 0.15) * 2.5}
                fill={theme.accent}
              />
              <circle
                cx={210 + Math.sin(frame * 0.06) * 8}
                cy={175 + Math.cos(frame * 0.06) * 6}
                r={17 + Math.sin(frame * 0.15) * 4}
                stroke={theme.accent}
                strokeWidth="2.5"
                fill="none"
              />
              <polyline
                points={`${210 + Math.sin(frame * 0.06) * 8},${175 + Math.cos(frame * 0.06) * 6} 265,92 315,92`}
                fill="none"
                stroke={theme.accent}
                strokeWidth="3"
                strokeLinecap="round"
              />
            </svg>

            <div
              style={{
                position: "absolute",
                top: 68,
                left: 312,
                right: 16,
                background: "rgba(4, 20, 15, 0.90)",
                border: `2px solid ${theme.accent}`,
                borderRadius: 10,
                padding: "6px 12px",
                fontSize: 15,
                fontWeight: 900,
                color: theme.accent,
                letterSpacing: 0.7,
                transform: `scale(${pointerAnim})`,
                transformOrigin: "left center",
                boxShadow: "0 6px 16px rgba(0,0,0,0.65)"
              }}
            >
              🎯 {pointerText}
            </div>

            <div
              style={{
                position: "absolute",
                left: 14,
                right: 14,
                bottom: 12,
                background: "rgba(4, 22, 17, 0.88)",
                border: `1.5px solid ${theme.accent}`,
                borderRadius: 12,
                padding: "6px 14px",
                fontSize: 16,
                fontWeight: 800,
                color: theme.soft,
                textAlign: "center",
                letterSpacing: 0.6
              }}
            >
              🎬 {styleBadgeText} • SCENE {String(scene.scene_number).padStart(2, "0")}
            </div>
          </div>
        )}
      </div>

      {/* Bottom Golden Dalil / Hikmah Card */}
      {scene.highlight_box && (
        <div
          style={{
            position: "absolute",
            left: 72,
            right: 72,
            bottom: visibleSubWords.length > 0 ? 78 : 42,
            background: `linear-gradient(90deg, rgba(6,28,22,0.96) 0%, ${theme.card} 100%)`,
            border: `3px solid ${theme.accent}`,
            borderLeft: `14px solid ${theme.accent}`,
            borderRadius: 18,
            padding: "13px 24px",
            transform: `translateY(${interpolate(boxAnim, [0, 1], [70, 0])}px)`,
            opacity: boxAnim
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              fontSize: 18,
              fontWeight: 900,
              color: theme.accent,
              letterSpacing: 1.3,
              marginBottom: 2
            }}
          >
            <span>✨ HIKMAH, SAINS & DALIL UTAMA</span>
          </div>
          <div
            style={{
              fontSize: 25,
              fontWeight: 800,
              color: "#ffffff",
              lineHeight: 1.24
            }}
          >
            “{scene.highlight_box}”
          </div>
        </div>
      )}

      {/* Synchronized Word-by-Word Kinetic Subtitle Bar (Motion Format `sub` feature) */}
      {visibleSubWords.length > 0 && (
        <div
          style={{
            position: "absolute",
            left: 72,
            right: 72,
            bottom: 20,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: 10,
            background: "rgba(3, 14, 11, 0.85)",
            border: `1.5px solid ${theme.accent}66`,
            borderRadius: 999,
            padding: "7px 26px"
          }}
        >
          <span style={{ fontSize: 18, fontWeight: 900, color: theme.accent, marginRight: 4 }}>
            🗣️
          </span>
          {visibleSubWords.map((w, idx) => {
            const globalIdx = subChunkIndex * subChunkSize + idx;
            const isSpokenNow = globalIdx === currentWordIndex;
            return (
              <span
                key={globalIdx}
                style={{
                  fontSize: 22,
                  fontWeight: isSpokenNow ? 900 : 700,
                  color: isSpokenNow ? "#041c15" : "#ffffff",
                  background: isSpokenNow ? theme.accent : "transparent",
                  padding: isSpokenNow ? "2px 10px" : "2px 3px",
                  borderRadius: 8,
                  transform: isSpokenNow ? "scale(1.08)" : "scale(1)"
                }}
              >
                {w}
              </span>
            );
          })}
        </div>
      )}

      {/* Animated Global Video Progress Bar at Bottom */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          height: 10,
          background: "rgba(255,255,255,0.12)"
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${overallProgress}%`,
            background: `linear-gradient(90deg, ${theme.accent} 0%, #ffffff 100%)`,
            boxShadow: `0 0 16px ${theme.accent}`
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

export const ExplainerVideo: React.FC<ExplainerProps> = ({
  topicTitle,
  targetAudience,
  scenes
}) => {
  let currentStart = 0;
  const total = scenes.length;

  return (
    <AbsoluteFill style={{ backgroundColor: "#031510" }}>
      {scenes.map((sc, i) => {
        const dur = Math.max(30, sc.durationInFrames || 300);
        const from = currentStart;
        currentStart += dur;
        return (
          <Sequence key={i} from={from} durationInFrames={dur}>
            <SceneCard
              scene={sc}
              totalScenes={total}
              topicTitle={topicTitle}
              targetAudience={targetAudience}
            />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
