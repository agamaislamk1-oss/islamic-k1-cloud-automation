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
  { bg1: string; bg2: string; card: string; accent: string; soft: string }
> = {
  emerald_gold: {
    bg1: "#072a22",
    bg2: "#031511",
    card: "rgba(14, 64, 52, 0.90)",
    accent: "#ffd21e",
    soft: "#fff2b9"
  },
  royal_teal: {
    bg1: "#082d3a",
    bg2: "#041620",
    card: "rgba(14, 68, 86, 0.90)",
    accent: "#50e1d2",
    soft: "#d2fcf8"
  },
  midnight_amber: {
    bg1: "#121e38",
    bg2: "#070e1e",
    card: "rgba(28, 46, 82, 0.90)",
    accent: "#ffbe28",
    soft: "#ffeeae"
  },
  deep_ocean: {
    bg1: "#0a2642",
    bg2: "#041224",
    card: "rgba(18, 58, 98, 0.90)",
    accent: "#78d2ff",
    soft: "#d7f2ff"
  },
  warm_emerald: {
    bg1: "#0e3026",
    bg2: "#061812",
    card: "rgba(22, 74, 58, 0.90)",
    accent: "#f5d75a",
    soft: "#fff8d2"
  }
};

const SceneCard: React.FC<{
  scene: SceneItem;
  totalScenes: number;
  targetAudience: string;
}> = ({ scene, totalScenes, targetAudience }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dur = Math.max(60, scene.durationInFrames || 300);
  const theme = THEMES[scene.theme_name] || THEMES.emerald_gold;

  // Spring animations for header, bullet cards, and highlight box
  const headerSpring = spring({ frame, fps, config: { damping: 14, stiffness: 110 } });
  const bulletStart1 = Math.floor(dur * 0.14);
  const bulletStart2 = Math.floor(dur * 0.34);
  const bulletStart3 = Math.floor(dur * 0.54);
  const boxStart = Math.floor(dur * 0.72);

  const b1 = spring({ frame: frame - bulletStart1, fps, config: { damping: 13 } });
  const b2 = spring({ frame: frame - bulletStart2, fps, config: { damping: 13 } });
  const b3 = spring({ frame: frame - bulletStart3, fps, config: { damping: 13 } });
  const boxAnim = spring({ frame: frame - boxStart, fps, config: { damping: 12 } });

  const fadeOut = interpolate(frame, [dur - 12, dur], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp"
  });
  const progressWidth = interpolate(frame, [0, dur], [0, 100], {
    extrapolateRight: "clamp"
  });

  const points = (scene.bullet_points || []).slice(0, 3);
  const bulletSprings = [b1, b2, b3];

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at 20% 20%, ${theme.bg1} 0%, ${theme.bg2} 100%)`,
        fontFamily: "'DejaVu Sans', 'Segoe UI', Arial, sans-serif",
        color: "#ffffff",
        padding: "56px 76px",
        opacity: fadeOut,
        overflow: "hidden"
      }}
    >
      {/* Animated subtle Islamic geometric glow rings */}
      <div
        style={{
          position: "absolute",
          right: -120,
          bottom: -120,
          width: 560,
          height: 560,
          borderRadius: "50%",
          border: `3px solid ${theme.accent}33`,
          transform: `rotate(${frame * 0.25}deg) scale(${1 + Math.sin(frame * 0.04) * 0.03})`
        }}
      />

      {/* Top Badge & Scene Indicator */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 18,
          transform: `translateY(${interpolate(headerSpring, [0, 1], [-30, 0])}px)`,
          opacity: headerSpring
        }}
      >
        <div
          style={{
            background: theme.accent,
            color: "#062019",
            fontWeight: 800,
            fontSize: 22,
            padding: "10px 26px",
            borderRadius: 999,
            letterSpacing: 1
          }}
        >
          BAGIAN {scene.scene_number}/{totalScenes} • {scene.section_badge}
        </div>
        <div
          style={{
            background: "rgba(255,255,255,0.12)",
            color: theme.soft,
            fontWeight: 700,
            fontSize: 20,
            padding: "9px 22px",
            borderRadius: 999,
            border: `1.5px solid ${theme.accent}66`
          }}
        >
          AUDIENS: {targetAudience.toUpperCase()}
        </div>
      </div>

      {/* Main Kinetic Headline */}
      <div
        style={{
          marginTop: 26,
          fontSize: 52,
          fontWeight: 900,
          lineHeight: 1.18,
          color: "#ffffff",
          textShadow: "0 6px 18px rgba(0,0,0,0.55)",
          maxWidth: 1620,
          transform: `scale(${interpolate(headerSpring, [0, 1], [0.92, 1])})`,
          transformOrigin: "left center"
        }}
      >
        {scene.headline}
      </div>

      {/* 3 Staggered Bullet Point Cards */}
      <div
        style={{
          marginTop: 34,
          display: "flex",
          flexDirection: "column",
          gap: 20,
          maxWidth: 1680
        }}
      >
        {points.map((pt, idx) => {
          const sp = bulletSprings[idx] ?? 1;
          return (
            <div
              key={idx}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 24,
                background: theme.card,
                border: `2.5px solid ${theme.accent}`,
                borderRadius: 22,
                padding: "22px 30px",
                boxShadow: "0 12px 28px rgba(0,0,0,0.35)",
                transform: `translateX(${interpolate(sp, [0, 1], [-80, 0])}px)`,
                opacity: sp
              }}
            >
              <div
                style={{
                  minWidth: 56,
                  height: 56,
                  borderRadius: "50%",
                  background: theme.accent,
                  color: "#062019",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 28,
                  fontWeight: 900
                }}
              >
                {idx + 1}
              </div>
              <div
                style={{
                  fontSize: 32,
                  fontWeight: 700,
                  lineHeight: 1.3,
                  color: "#ffffff"
                }}
              >
                {pt}
              </div>
            </div>
          );
        })}
      </div>

      {/* Highlight Dalil / Hikmah Footer Card */}
      {scene.highlight_box && (
        <div
          style={{
            position: "absolute",
            left: 76,
            right: 76,
            bottom: 52,
            background: `linear-gradient(90deg, ${theme.accent}26 0%, ${theme.card} 100%)`,
            borderLeft: `10px solid ${theme.accent}`,
            borderRadius: 18,
            padding: "20px 30px",
            boxShadow: "0 10px 26px rgba(0,0,0,0.45)",
            transform: `translateY(${interpolate(boxAnim, [0, 1], [50, 0])}px)`,
            opacity: boxAnim
          }}
        >
          <div
            style={{
              fontSize: 20,
              fontWeight: 800,
              color: theme.accent,
              letterSpacing: 1.2,
              marginBottom: 4
            }}
          >
            ★ INTISARI DALIL & HIKMAH UTAMA
          </div>
          <div
            style={{
              fontSize: 28,
              fontWeight: 700,
              color: theme.soft,
              lineHeight: 1.3
            }}
          >
            {scene.highlight_box}
          </div>
        </div>
      )}

      {/* Bottom Progress Bar */}
      <div
        style={{
          position: "absolute",
          left: 0,
          bottom: 0,
          height: 10,
          width: `${progressWidth}%`,
          background: theme.accent
        }}
      />
    </AbsoluteFill>
  );
};

export const ExplainerVideo: React.FC<ExplainerProps> = ({
  targetAudience,
  scenes
}) => {
  let currentStart = 0;
  const total = scenes.length;

  return (
    <AbsoluteFill style={{ backgroundColor: "#041612" }}>
      {scenes.map((sc, i) => {
        const dur = Math.max(30, sc.durationInFrames || 300);
        const from = currentStart;
        currentStart += dur;
        return (
          <Sequence key={i} from={from} durationInFrames={dur}>
            <SceneCard
              scene={sc}
              totalScenes={total}
              targetAudience={targetAudience}
            />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
