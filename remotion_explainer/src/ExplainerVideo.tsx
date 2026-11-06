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
        width: 112,
        height: 112,
        borderRadius: 28,
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
        <svg width="68" height="68" viewBox="0 0 24 24" fill={accent}>
          <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" />
        </svg>
      ) : iconType === "book" ? (
        <svg width="64" height="64" viewBox="0 0 24 24" fill={accent}>
          <path d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4z" />
        </svg>
      ) : iconType === "lightbulb" ? (
        <svg width="64" height="64" viewBox="0 0 24 24" fill={accent}>
          <path d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7z" />
        </svg>
      ) : iconType === "heart" ? (
        <svg width="64" height="64" viewBox="0 0 24 24" fill={accent}>
          <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
        </svg>
      ) : iconType === "shield" ? (
        <svg width="64" height="64" viewBox="0 0 24 24" fill={accent}>
          <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z" />
        </svg>
      ) : (
        <svg width="66" height="66" viewBox="0 0 24 24" fill={accent}>
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

  // Dynamic entrance & exit animations
  const headerSpring = spring({ frame, fps, config: { damping: 12, stiffness: 120 } });
  const bulletStart1 = Math.floor(dur * 0.12);
  const bulletStart2 = Math.floor(dur * 0.32);
  const bulletStart3 = Math.floor(dur * 0.52);
  const boxStart = Math.floor(dur * 0.68);

  const b1 = spring({ frame: frame - bulletStart1, fps, config: { damping: 12, stiffness: 110 } });
  const b2 = spring({ frame: frame - bulletStart2, fps, config: { damping: 12, stiffness: 110 } });
  const b3 = spring({ frame: frame - bulletStart3, fps, config: { damping: 12, stiffness: 110 } });
  const boxAnim = spring({ frame: frame - boxStart, fps, config: { damping: 11, stiffness: 105 } });

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

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at 20% 20%, ${theme.bg1} 0%, ${theme.bg2} 100%)`,
        fontFamily: "'Segoe UI', 'DejaVu Sans', Arial, sans-serif",
        color: "#ffffff",
        padding: "46px 72px",
        opacity: fadeOut,
        overflow: "hidden"
      }}
    >
      {/* Animated Floating Geometric Mandala & Particles */}
      <svg
        width="760"
        height="760"
        viewBox="0 0 200 200"
        style={{
          position: "absolute",
          right: -160,
          top: 120,
          opacity: 0.14,
          transform: `rotate(${frame * 0.35}deg) scale(${1 + Math.sin(frame * 0.03) * 0.06})`
        }}
      >
        <circle cx="100" cy="100" r="88" stroke={theme.accent} strokeWidth="2" fill="none" strokeDasharray="8 6" />
        <circle cx="100" cy="100" r="68" stroke={theme.accent} strokeWidth="1.5" fill="none" />
        <polygon points="100,15 185,100 100,185 15,100" stroke={theme.accent} strokeWidth="1.5" fill="none" />
        <polygon points="40,40 160,40 160,160 40,160" stroke={theme.accent} strokeWidth="1.5" fill="none" />
      </svg>

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
              width: 12 + (pIdx % 3) * 6,
              height: 12 + (pIdx % 3) * 6,
              borderRadius: "50%",
              background: theme.accent,
              opacity: 0.16,
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
          gap: 16,
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
            fontSize: 22,
            padding: "10px 26px",
            borderRadius: 999,
            letterSpacing: 1.2,
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
            fontSize: 20,
            padding: "10px 24px",
            borderRadius: 999,
            border: `2px solid ${theme.accent}77`
          }}
        >
          AUDIENS: {targetAudience.toUpperCase()} • {scene.section_badge.toUpperCase()}
        </div>

        {/* Live Voice Waveform Bars */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 5,
            marginLeft: "auto",
            marginRight: 40,
            background: "rgba(0,0,0,0.35)",
            padding: "8px 18px",
            borderRadius: 999,
            border: `1.5px solid ${theme.accent}55`
          }}
        >
          {[0, 1, 2, 3, 4, 5, 6, 7].map((bar) => {
            const h = 10 + Math.abs(Math.sin(frame * 0.25 + bar * 0.9)) * 20;
            return (
              <div
                key={bar}
                style={{
                  width: 5,
                  height: h,
                  borderRadius: 4,
                  background: theme.accent
                }}
              />
            );
          })}
          <span style={{ marginLeft: 10, fontSize: 16, fontWeight: 800, color: theme.accent }}>
            REMOTION HD
          </span>
        </div>
      </div>

      {/* Main Kinetic Hero Section with Floating Icon & Word-by-Word Spring Headline */}
      <div
        style={{
          marginTop: 24,
          display: "flex",
          alignItems: "center",
          gap: 28,
          maxWidth: 1680
        }}
      >
        <DynamicSvgIcon
          iconType={scene.icon_type}
          accent={theme.accent}
          frame={frame}
          topicTitle={topicTitle}
        />

        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "12px" }}>
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
                    fontSize: 52,
                    fontWeight: 900,
                    lineHeight: 1.12,
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
              fontSize: 23,
              fontWeight: 800,
              color: theme.soft,
              letterSpacing: 1.1,
              opacity: 0.9
            }}
          >
            TOPIK: {topicTitle.toUpperCase()}
          </div>
        </div>
      </div>

      {/* 3 Staggered 3D Spring Cards with Active Spotlight Glow */}
      <div
        style={{
          marginTop: 28,
          display: "flex",
          flexDirection: "column",
          gap: 18,
          maxWidth: 1740
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
                gap: 24,
                background: isCurrent
                  ? `linear-gradient(90deg, ${theme.card} 0%, ${theme.accent}28 100%)`
                  : theme.card,
                border: isCurrent ? `3.5px solid ${theme.accent}` : `2px solid rgba(255,255,255,0.22)`,
                borderRadius: 22,
                padding: "20px 28px",
                transform: `translateX(${interpolate(sp, [0, 1], [-120, 0])}px) scale(${interpolate(sp, [0, 1], [0.9, pulseScale])})`,
                opacity: sp
              }}
            >
              <div
                style={{
                  minWidth: 64,
                  height: 64,
                  borderRadius: 18,
                  background: isCurrent ? theme.accent : "rgba(255,255,255,0.14)",
                  color: isCurrent ? "#041c15" : theme.accent,
                  border: `2px solid ${theme.accent}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 30,
                  fontWeight: 900,
                  boxShadow: isCurrent ? `0 0 18px ${theme.accent}88` : "none"
                }}
              >
                0{idx + 1}
              </div>
              <div
                style={{
                  fontSize: 33,
                  fontWeight: 800,
                  lineHeight: 1.26,
                  color: isCurrent ? "#ffffff" : theme.soft
                }}
              >
                {pt}
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom Golden Dalil / Hikmah Card */}
      {scene.highlight_box && (
        <div
          style={{
            position: "absolute",
            left: 72,
            right: 72,
            bottom: 50,
            background: `linear-gradient(90deg, rgba(6,28,22,0.96) 0%, ${theme.card} 100%)`,
            border: `3px solid ${theme.accent}`,
            borderLeft: `14px solid ${theme.accent}`,
            borderRadius: 20,
            padding: "18px 28px",
            transform: `translateY(${interpolate(boxAnim, [0, 1], [70, 0])}px)`,
            opacity: boxAnim
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              fontSize: 20,
              fontWeight: 900,
              color: theme.accent,
              letterSpacing: 1.4,
              marginBottom: 4
            }}
          >
            <span>✨ HIKMAH, SAINS & DALIL UTAMA</span>
          </div>
          <div
            style={{
              fontSize: 28,
              fontWeight: 800,
              color: "#ffffff",
              lineHeight: 1.28
            }}
          >
            “{scene.highlight_box}”
          </div>
        </div>
      )}

      {/* Animated Global Video Progress Bar at Bottom */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          height: 12,
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
