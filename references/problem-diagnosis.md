# Problem Diagnosis Reference

Use this reference when the user needs to rescue a photo, diagnose editing problems, or understand why a beginner image looks weak.

## General Repair Order

1. Fix exposure and white balance.
2. Recover important highlights and shadows.
3. Clean skin tone or main subject color.
4. Improve subject separation with local masks.
5. Reduce distractions.
6. Add style only after the image is technically stable.

## Face Too Dark

Symptoms:
- Face is darker than the background.
- Eyes look dull.
- Skin lacks separation from hair or clothing.

Likely cause:
- Backlight, overhead light, underexposure, or camera metering for the background.

Priority:
- High for portraits and selfies.

Lightroom direction:
- Raise Exposure `+0.2 to +0.6` only if the whole image is underexposed.
- Use a subject or face mask: Exposure `+0.3 to +0.8`, Shadows `+15 to +40`, Whites `+5 to +15`.
- Add a small amount of Texture `-5 to -15` for skin, but keep eyes and hair sharp.
- If the background becomes too bright, use a separate background mask: Exposure `-0.2 to -0.6`.

Phone app translation:
- Use portrait/face adjustment if available.
- Increase face brightness, reduce background brightness, then add mild sharpening to eyes.

AI prompt guidance:
- "Brighten the subject's face naturally, preserve realistic skin texture, keep background exposure controlled, maintain original identity and facial structure."

Mistakes to avoid:
- Do not brighten the whole image until the background is washed out.
- Do not over-smooth skin.

## Dirty Or Uneven Skin Tone

Symptoms:
- Skin looks gray, green, orange, red, or patchy.
- Face color does not match neck or hands.

Likely cause:
- Mixed lighting, wrong white balance, excessive saturation, or cheap phone HDR.

Priority:
- High for portraits.

Lightroom direction:
- Correct white balance before HSL.
- Reduce Orange Saturation `-5 to -15` if skin is too orange.
- Raise Orange Luminance `+5 to +20` for cleaner skin.
- Reduce Red Saturation `-5 to -20` for blotchy redness.
- Use Color Mix carefully; skin usually lives in red, orange, and yellow.

Phone app translation:
- Adjust temperature and tint first.
- Use skin tone or portrait color tools lightly.
- Avoid one-click beauty filters that erase texture.

AI prompt guidance:
- "Clean and even natural skin tone, reduce color blotches, preserve pores and realistic texture, avoid plastic skin."

Mistakes to avoid:
- Do not make skin pure white.
- Do not use heavy blur to solve color problems.

## Backlit Subject

Symptoms:
- Background is bright while the subject is dark.
- Hair edge may glow but face lacks detail.

Likely cause:
- Strong light behind subject, camera exposed for sky or window.

Priority:
- High for portraits and travel photos with people.

Lightroom direction:
- Lower Highlights `-30 to -80`.
- Raise Shadows `+20 to +60`.
- Mask subject: Exposure `+0.3 to +0.9`, Shadows `+20 to +50`.
- Add a subtle warm tone to highlights if the backlight is sunset.
- Reduce haze only if the image becomes washed out.

Phone app translation:
- Use selective adjustment on the person.
- Pull down highlights or sky brightness separately.

AI prompt guidance:
- "Recover the backlit subject, brighten face and body naturally, keep rim light, preserve bright background detail without making the image flat."

Mistakes to avoid:
- Do not make shadows muddy by pushing them too far.
- Do not remove the backlight glow completely.

## Overexposed Sky

Symptoms:
- Sky is white or lacks cloud detail.
- Landscape foreground may be darker.

Likely cause:
- High dynamic range scene, midday light, phone HDR failure.

Priority:
- High for travel landscapes.

Lightroom direction:
- Lower Highlights `-50 to -100`.
- Lower Whites `-10 to -35`.
- Use sky mask: Exposure `-0.2 to -0.8`, Highlights `-40 to -80`, Dehaze `+5 to +20`.
- If sky detail is clipped, avoid pretending detail exists; use a cleaner crop or AI sky recovery if allowed.

Phone app translation:
- Use sky or selective tool.
- Reduce highlight and add slight blue saturation only after exposure is controlled.

AI prompt guidance:
- "Recover a natural sky with soft cloud detail, avoid fake dramatic clouds, match the original lighting direction."

Mistakes to avoid:
- Do not make the sky neon blue.
- Do not add a sky that conflicts with the scene light.

## Gray And Flat Image

Symptoms:
- Image lacks contrast and depth.
- Whites are dull and blacks are weak.
- Colors feel lifeless.

Likely cause:
- Haze, low contrast light, under-edited raw file, or phone processing.

Priority:
- Medium to high for landscapes and street photos.

Lightroom direction:
- Set white and black points first: Whites `+5 to +25`, Blacks `-10 to -35`.
- Add a gentle S-curve.
- Use Dehaze `+3 to +15` for outdoor haze.
- Add Vibrance `+5 to +20`, not heavy Saturation.

Phone app translation:
- Increase contrast slightly.
- Add clarity or structure carefully.
- Use warmth or color only after contrast improves.

AI prompt guidance:
- "Add natural depth and contrast, improve tonal separation, keep realistic colors, avoid oversaturated HDR."

Mistakes to avoid:
- Do not fix flatness only by increasing saturation.
- Do not crush all shadow detail.

## Distracting Background

Symptoms:
- Background objects compete with the subject.
- Bright areas or clutter pull attention away.

Likely cause:
- Busy scene, weak composition, wide-angle perspective, or no subject separation.

Priority:
- High for portraits and street photos.

Lightroom direction:
- Crop to remove edge distractions.
- Mask background: Exposure `-0.2 to -0.7`, Clarity `-5 to -20`, Saturation `-5 to -20`.
- Mask subject: Texture `+5 to +15`, Exposure `+0.1 to +0.4`.
- Add vignette only subtly.

Phone app translation:
- Crop first.
- Use background blur or selective darkening if natural.

AI prompt guidance:
- "Reduce background distractions, subtly darken and soften background, keep subject sharp and natural, preserve original scene."

Mistakes to avoid:
- Do not apply fake blur with rough edges.
- Do not crop so tightly that the subject loses context.

## High ISO Night Noise

Symptoms:
- Grainy shadows, color speckles, muddy details.
- Night image looks dirty rather than atmospheric.

Likely cause:
- Small sensor, high ISO, underexposure, or aggressive shadow recovery.

Priority:
- High for night street and travel photos.

Lightroom direction:
- Avoid pushing shadows too far.
- Noise Reduction Luminance `15 to 40`.
- Color Noise Reduction `20 to 40`.
- Add sharpening with masking so flat areas are not sharpened.
- Consider black-and-white or high-contrast night style if color quality is poor.

Phone app translation:
- Use denoise lightly.
- Reduce shadow recovery.
- Add grain only after cleaning color noise.

AI prompt guidance:
- "Reduce color noise and muddy shadows, preserve night atmosphere and important details, avoid waxy over-smoothed texture."

Mistakes to avoid:
- Do not denoise until skin, walls, and sky look plastic.
- Do not brighten every shadow.

## Weak Or Flat Lighting

Symptoms:
- Subject looks shapeless.
- No clear highlight-shadow structure.
- Portrait lacks dimension.

Likely cause:
- Cloudy light, front-facing phone flash, indoor ambient light, or flat angle.

Priority:
- High for portraits.

Lightroom direction:
- Use masks to create direction: brighten face side slightly and darken background or non-key side.
- Add Contrast `+5 to +20`.
- Add a mild S-curve.
- Use Dodge and Burn style masks for cheekbones, hair, and clothing folds.

Phone app translation:
- Use selective brightness and shadow tools.
- Add contrast locally instead of only using global contrast.

AI prompt guidance:
- "Create subtle natural light direction, add soft dimensional shadows, improve subject separation, keep realistic lighting."

Mistakes to avoid:
- Do not add harsh artificial shadows that contradict the original light.
- Do not overuse clarity on skin.

## Color Cast

Symptoms:
- Whole image is too green, magenta, blue, or yellow.
- Whites and grays are not neutral.

Likely cause:
- Artificial lighting, shade, mixed light, or wrong white balance.

Priority:
- High before any style work.

Lightroom direction:
- Use white balance eyedropper on a neutral area if available.
- Adjust Temperature for blue/yellow cast.
- Adjust Tint for green/magenta cast.
- After neutralizing, reintroduce style color with Color Grading.

Phone app translation:
- Use temperature and tint first.
- Do not use filters before correcting color cast.

AI prompt guidance:
- "Correct unnatural color cast, make neutral surfaces believable, preserve intended mood and natural skin tone."

Mistakes to avoid:
- Do not fight color cast with saturation.
- Do not make all scenes perfectly neutral if the mood light is meaningful.

## Low Subject Separation

Symptoms:
- Subject blends into background.
- Photo has no clear visual hierarchy.

Likely cause:
- Similar brightness, similar color, busy background, or weak focus.

Priority:
- High for portraits and street photos.

Lightroom direction:
- Mask subject: Exposure `+0.1 to +0.4`, Texture `+5 to +15`.
- Mask background: Exposure `-0.2 to -0.5`, Saturation `-5 to -20`.
- Use color contrast: warm subject against cooler background, or the reverse.
- Crop to strengthen subject placement.

Phone app translation:
- Selectively brighten subject.
- Slightly darken or desaturate background.

AI prompt guidance:
- "Improve subject separation with subtle light and color contrast, keep edges natural, preserve original background context."

Mistakes to avoid:
- Do not create an obvious cutout effect.
- Do not over-sharpen the subject.

## Weak Composition

Symptoms:
- Subject is too centered without intent.
- Important elements are cut awkwardly.
- Edge distractions pull attention.

Likely cause:
- Fast shooting, no crop, unclear subject priority.

Priority:
- Medium, but often decisive.

Lightroom direction:
- Crop before color grading.
- Use 4:5 for portraits, 3:2 or 16:9 for landscapes when appropriate.
- Straighten horizon.
- Remove or darken edge distractions.

Phone app translation:
- Crop and straighten first.
- Use vignette or selective darkening only after crop.

AI prompt guidance:
- "Improve composition through natural crop and distraction reduction, keep original subject and scene, avoid changing identity or key content."

Mistakes to avoid:
- Do not rely on color grading to fix unclear composition.
- Do not crop away important context.
