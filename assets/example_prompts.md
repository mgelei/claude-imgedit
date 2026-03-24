# Example Edit Prompts

A reference of effective prompts for AI image editing, organized by category.

## Background Changes

- **"Remove the background and make it transparent"** — Works best with clear subject/background separation. Use `quality=high`.
- **"Replace the background with a tropical beach at sunset"** — Be specific about the scene for better results.
- **"Blur the background to create a portrait bokeh effect"** — Simulates shallow depth of field.

## Style Transfer

- **"Make it look like a watercolor painting"** — Softens edges and adds paint-bleed texture.
- **"Convert to a pencil sketch"** — Best on images with strong contrast and clear outlines.
- **"Apply a vintage 1970s film look"** — Adds grain, faded tones, and warm color shift.
- **"Render in the style of a comic book with bold outlines"** — Works well on portraits and action shots.
- **"Make it look like pixel art"** — Specify a resolution hint (e.g., "16-bit style") for consistency.

## Multi-Image Edits

- **"Convert the photo to a drawing, use the other image as style guidance"** — Pass both uploaded images through and keep the user's phrasing intact.
- **"Apply the outfit from the selfie to the photo of the woman with glasses"** — Do not rename the uploads with ordinal or role labels in the forwarded prompt.

## Object Manipulation

- **"Add aviator sunglasses to the person"** — Face should be clearly visible and front-facing.
- **"Remove the person standing in the background"** — Works best when the background is simple or repetitive.
- **"Replace the car with a bicycle"** — Describe the replacement object's style/color for a natural fit.
- **"Make the dog in the foreground larger"** — Subtle size changes look more realistic than extreme ones.

## Color & Lighting

- **"Increase the brightness and add more contrast"** — Good for underexposed photos.
- **"Make the colors warmer with golden tones"** — Shifts the palette toward amber/orange.
- **"Convert to black and white with high contrast"** — Specify "high contrast" to avoid flat results.
- **"Add dramatic side lighting as if from a window"** — Describe light direction for best effect.
- **"Change the lighting to look like sunset golden hour"** — Adds warm tones and long shadows.

## Text & Overlays

- **"Add the text 'Hello World' in bold white across the top"** — Specify font style, color, and position.
- **"Add a subtle watermark saying 'DRAFT' in the center"** — Use "subtle" or "semi-transparent" for non-intrusive results.
- **"Add a thin black border around the image"** — Specify thickness and color for precise control.

## Face & Portrait Edits

- **"Change the hair color to bright red"** — Works best on clearly visible, unstyled hair.
- **"Add round glasses to the person"** — Front-facing, well-lit faces yield the most natural results.
- **"Make the person look 20 years older"** — Subtle aging looks more convincing. Use `quality=high`.
- **"Change the expression to a smile"** — Works best when the face is large and unobstructed.

## Scene Modifications

- **"Make it look like winter with snow on the ground"** — Works well on outdoor landscape photos.
- **"Add heavy rain and overcast skies"** — Combine weather and sky changes in one prompt for cohesion.
- **"Turn this city street into a forest path"** — Drastic environment swaps work better at `quality=high`.

## Photo Enhancement

- **"Upscale and enhance the image quality"** — Best for slightly soft images; won't recover extreme blur.
- **"Remove the noise and grain from this low-light photo"** — Preserves detail better when you specify "keep sharpness."
- **"Fix the perspective so the building lines are straight"** — Useful for architectural photos with lens distortion.

## Tips

- **Be specific**: "a sunny beach with palm trees" beats "a nice background."
- **Combine edits carefully**: chaining too many changes in one prompt can reduce quality.
- **Use `quality=high`** for detail-sensitive work like faces, text, or fine textures.
