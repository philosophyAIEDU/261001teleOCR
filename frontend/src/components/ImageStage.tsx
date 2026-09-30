import { useState } from "react";
import type { CropBox, LayoutBlock } from "../types";
import CropTool from "./CropTool";
import LayoutOverlay from "./LayoutOverlay";

interface Props {
  src: string;
  alt: string;
  cropMode: boolean;
  crop: CropBox | null;
  onCropChange: (crop: CropBox | null) => void;
  blocks: LayoutBlock[] | null;
  onSelectBlock?: (block: LayoutBlock) => void;
}

export default function ImageStage({ src, alt, cropMode, crop, onCropChange, blocks, onSelectBlock }: Props) {
  const [failed, setFailed] = useState(false);
  return (
    <div className="flex justify-center overflow-auto rounded-2xl border border-slate-300 bg-slate-200 p-2">
      <div className="relative inline-block max-w-full">
        {failed ? (
          <p className="p-8">이미지를 불러오지 못했어요. 파일을 다시 올려 주세요.</p>
        ) : (
          <img src={src} alt={alt} className="block max-h-[75vh] max-w-full select-none" draggable={false} onError={() => setFailed(true)} />
        )}
        {blocks && blocks.length > 0 && !cropMode && <LayoutOverlay blocks={blocks} onSelect={onSelectBlock} />}
        {cropMode && <CropTool value={crop} onChange={onCropChange} />}
      </div>
    </div>
  );
}
