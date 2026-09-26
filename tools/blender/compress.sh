#!/usr/bin/env bash
# Compress the HariBatti GLB set in place: Draco geometry + WebP textures (KTX2 needs Khronos
# toktx, which is not available here; WebP is the fallback). Keeps object names (wheel_*, lamps).
# Also writes the shared palette textures the website uses for every model.
set -euo pipefail
cd "$(dirname "$0")/../.."
GT="npx -y @gltf-transform/cli@4.5.0"
for f in apps/web/public/models/vehicles/*.glb apps/web/public/models/city/*.glb; do
  tmp="${f%.glb}.tmp.glb"
  $GT optimize "$f" "$tmp" --compress draco --texture-compress webp --simplify false --join false \
    --flatten false --instance false --palette false --weld false >/dev/null
  mv "$tmp" "$f"
done
npx -y sharp-cli@5 -i tools/blender/palette.png -o apps/web/public/models/palette.webp -f webp --lossless >/dev/null 2>&1 \
  || cp tools/blender/palette.png apps/web/public/models/palette.png
npx -y sharp-cli@5 -i tools/blender/palette_mr.png -o apps/web/public/models/palette_mr.webp -f webp --lossless >/dev/null 2>&1 \
  || cp tools/blender/palette_mr.png apps/web/public/models/palette_mr.png
npx -y sharp-cli@5 -i tools/blender/palette_em.png -o apps/web/public/models/palette_em.webp -f webp --lossless >/dev/null 2>&1 \
  || cp tools/blender/palette_em.png apps/web/public/models/palette_em.png
du -ch apps/web/public/models/vehicles/*.glb | tail -1
