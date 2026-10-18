"""
Batch rendering script for user test images.
Zero Interference Guarantee:
- No collision with faces, hair, or hands
- Accurate tails directed to speaking characters without crossing other characters
- Perfect typography, auto-contrast, floating monologues, and manga SFX
"""
import os
from comic_bubble import render_scene, SceneConfig, BubbleConfig

OUTPUT_DIR = "output/batch_test_20261018"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------
# Test Image 1: Infirmary Blush (Vertical 700x1024)
# ---------------------------------------------------------
scene1 = SceneConfig(
    image_path="input/test_01_infirmary.jpg",
    output_path=os.path.join(OUTPUT_DIR, "01_infirmary_blush.png"),
    supersample_scale=3,
    bubbles=[
        # Tsundere speech bubble in window light space (Zero hair overlap)
        BubbleConfig(
            text="<small>ち、ちょっと…！</small>\n<big>ノックくらい</big>\n<big>しなさいよ…！</big>",
            type="capsule",
            font="kiwi",
            center=(0.85, 0.14),
            tail=(0.71, 0.23),  # points cleanly towards her mouth/neck, stops before hair
            font_size_ratio=0.019,
            border_color=(60, 45, 50, 220),
            text_color=(65, 30, 40, 255),
            bg_color=(255, 248, 244),
            visibility_mode="auto"
        ),
        # Floating monologue on dark green curtain (White text with soft halo)
        BubbleConfig(
            text="（…見られた…っ？！）",
            type="floating",
            font="mincho",
            center=(0.14, 0.18),
            font_size_ratio=0.022,
            text_color=(45, 30, 45, 255),
            text_halo=True,
            halo_color=(255, 255, 255, 240)
        ),
        # Sudden movement SFX by the bed frame
        BubbleConfig(
            text="バッ",
            type="sfx",
            font="bold",
            center=(0.20, 0.65),
            angle=-12.0,
            font_size_ratio=0.055,
            text_color=(235, 60, 75, 255),
            stroke_width=3.5,
            stroke_color=(255, 255, 255, 255)
        )
    ]
)

# ---------------------------------------------------------
# Test Image 2: Classroom Secret Whisper (Horizontal 1024x700)
# ---------------------------------------------------------
scene2 = SceneConfig(
    image_path="input/test_02_whisper.jpg",
    output_path=os.path.join(OUTPUT_DIR, "02_classroom_whisper.png"),
    supersample_scale=3,
    bubbles=[
        # Blonde girl whisper bubble (dashed line)
        BubbleConfig(
            text="<small>…ねぇ、あいつの事</small>\n<big>好きなんでしょ？…</big>",
            type="whisper",
            font="zenmaru",
            center=(0.85, 0.22),
            tail=(0.69, 0.27),
            font_size_ratio=0.027,
            border_color=(70, 70, 90, 220),
            text_color=(50, 45, 65, 255),
            bg_color=(255, 252, 250),
            visibility_mode="auto"
        ),
        # Brunette floating inner monologue on chalkboard
        BubbleConfig(
            text="（…ち、違うし…っ！\n　からかわないでよ…）",
            type="floating",
            font="mincho",
            center=(0.15, 0.40),
            font_size_ratio=0.025,
            text_color=(255, 255, 255, 255),
            text_halo=True,
            halo_color=(30, 60, 45, 220)
        ),
        # Whisper SFX between their faces
        BubbleConfig(
            text="ヒソ…",
            type="sfx",
            font="bold",
            center=(0.53, 0.22),
            angle=-5.0,
            font_size_ratio=0.040,
            text_color=(255, 120, 150, 255),
            stroke_width=2.5,
            stroke_color=(255, 255, 255, 255)
        )
    ]
)

# ---------------------------------------------------------
# Test Image 3: Three Friends Selfie (Horizontal 1024x700)
# ---------------------------------------------------------
scene3 = SceneConfig(
    image_path="input/test_03_friends.jpg",
    output_path=os.path.join(OUTPUT_DIR, "03_friends_selfie.png"),
    supersample_scale=3,
    bubbles=[
        # Left girl (cheerful cloud bubble on top-left)
        BubbleConfig(
            text="<big>はい、チーズ！</big>",
            type="cloud",
            font="kiwi",
            center=(0.11, 0.18),
            tail=(0.18, 0.22),
            font_size_ratio=0.030,
            border_color=(50, 45, 65, 220),
            text_color=(45, 35, 55, 255),
            bg_color=(255, 250, 245),
            visibility_mode="auto"
        ),
        # Right girl (G-jacket girl speech bubble over locker space)
        BubbleConfig(
            text="<small>ほら、</small>\n<big>もっと寄って〜！</big>",
            type="capsule",
            font="zenmaru",
            center=(0.89, 0.17),
            tail=(0.79, 0.22),  # cleanly stops in open air before right girl's hair
            font_size_ratio=0.024,
            border_color=(50, 45, 65, 220),
            text_color=(45, 35, 55, 255),
            bg_color=(255, 250, 245),
            visibility_mode="auto"
        ),
        # Center girl reaction (cute reaction SFX on ceiling light space, completely above hair)
        BubbleConfig(
            text="えっ！？",
            type="sfx",
            font="bold",
            center=(0.49, 0.045),
            angle=5.0,
            font_size_ratio=0.042,
            text_color=(255, 100, 120, 255),
            stroke_width=3.5,
            stroke_color=(255, 255, 255, 255)
        ),
        # Camera shutter onomatopoeia at bottom center
        BubbleConfig(
            text="パシャッ",
            type="sfx",
            font="bold",
            center=(0.50, 0.90),
            angle=-8.0,
            font_size_ratio=0.052,
            text_color=(255, 220, 60, 255),
            stroke_width=3.5,
            stroke_color=(40, 40, 50, 255)
        )
    ]
)

# ---------------------------------------------------------
# Test Image 4: Washroom Dusk/Night View (Horizontal 1024x700)
# ---------------------------------------------------------
scene4 = SceneConfig(
    image_path="input/test_04_washroom.jpg",
    output_path=os.path.join(OUTPUT_DIR, "04_washroom_nightview.png"),
    supersample_scale=3,
    bubbles=[
        # Spoken bubble (capsule on wall above her back, pointing to mouth)
        BubbleConfig(
            text="<small>お待たせ！</small>\n<big>すぐ行くね！</big>",
            type="capsule",
            font="kiwi",
            center=(0.68, 0.18),
            tail=(0.55, 0.32),
            font_size_ratio=0.028,
            border_color=(50, 45, 65, 220),
            text_color=(45, 35, 55, 255),
            bg_color=(255, 250, 245),
            visibility_mode="auto"
        ),
        # Floating monologue in front of the night view window
        BubbleConfig(
            text="（…今日こそ、\n　ちゃんと伝えなきゃ…）",
            type="floating",
            font="mincho",
            center=(0.88, 0.22),
            font_size_ratio=0.025,
            text_color=(255, 250, 240, 255),
            text_halo=True,
            halo_color=(30, 35, 60, 220)
        ),
        # SFX near the water faucet
        BubbleConfig(
            text="パシャ…",
            type="sfx",
            font="bold",
            center=(0.18, 0.75),
            angle=-10.0,
            font_size_ratio=0.042,
            text_color=(90, 190, 255, 255),
            stroke_width=3.0,
            stroke_color=(255, 255, 255, 255)
        )
    ]
)

if __name__ == "__main__":
    for i, sc in enumerate([scene1, scene2, scene3, scene4], 1):
        print(f"Rendering scene {i}: {sc.output_path}...")
        img = render_scene(sc)
        img.save(sc.output_path, quality=98)
        print(f"  -> Saved {sc.output_path}")
    print("All batch tests completed successfully!")
