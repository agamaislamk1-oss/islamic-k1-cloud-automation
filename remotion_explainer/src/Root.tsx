import React from "react";
import { Composition } from "remotion";
import { ExplainerVideo, ExplainerProps, SceneItem } from "./ExplainerVideo";

const defaultScenes: SceneItem[] = [
  {
    scene_number: 1,
    section_badge: "PEMBUKAAN ISLAMI",
    headline: "Keutamaan Menuntut Ilmu dalam Islam",
    bullet_points: [
      "Menuntut ilmu adalah kewajiban setiap Muslim",
      "Allah mengangkat derajat orang yang berilmu",
      "Ilmu yang diamalkan menjadi amal jariyah abadi"
    ],
    highlight_box: "HR. Muslim: Barangsiapa menempuh jalan mencari ilmu, Allah mudahkan jalannya ke surga.",
    icon_type: "mosque",
    theme_name: "emerald_gold",
    durationInFrames: 300
  }
];

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="IslamicK1Explainer"
        component={ExplainerVideo}
        fps={12}
        width={1920}
        height={1080}
        defaultProps={{
          topicTitle: "Edukasi Keluarga Muslim",
          targetAudience: "Keluarga & Pelajar Muslim",
          scenes: defaultScenes
        }}
        calculateMetadata={({ props }) => {
          const totalFrames = (props.scenes || defaultScenes).reduce(
            (acc, s) => acc + Math.max(24, s.durationInFrames || 180),
            0
          );
          return {
            durationInFrames: Math.max(48, totalFrames),
            fps: 12,
            width: 1920,
            height: 1080
          };
        }}
      />
    </>
  );
};
