#!/usr/bin/env python3
"""
SOE Auto Editor - CLI & Agent 入口

用法:
  python agent_api.py video1.mp4 video2.mp4 -t party_building -o output.mp4
  python agent_api.py video.mp4 --preview
  python agent_api.py --serve
"""
import sys
import json
import asyncio
import argparse
import logging


def main():
    parser = argparse.ArgumentParser(
        prog="soe-edit",
        description="国企宣传视频自动剪辑工具",
    )
    parser.add_argument("videos", nargs="*", help="输入视频文件路径")
    parser.add_argument("-t", "--template", default="party_building",
                        choices=["party_building", "conference", "visit", "study"])
    parser.add_argument("-o", "--output", default="", help="输出文件路径")
    parser.add_argument("--title", default="", help="视频标题")
    parser.add_argument("--subtitle", default="", help="副标题")
    parser.add_argument("--org", default="", help="单位名称")
    parser.add_argument("--date", default="", help="日期文字")
    parser.add_argument("--duration", type=float, default=0, help="目标时长(秒)")
    parser.add_argument("--music", default=None, help="指定BGM路径")
    parser.add_argument("--logo", default=None, help="Logo路径")
    parser.add_argument("--tone", default=None,
                        help="调色预设名称（传统预设或LUT预设）")
    parser.add_argument("--lut", default=None,
                        help="LUT文件路径（.cube文件）")
    parser.add_argument("--list-luts", action="store_true",
                        help="列出所有可用的LUT预设")
    parser.add_argument("--list-tones", action="store_true",
                        help="列出所有可用的调色预设")
    parser.add_argument("--preview", action="store_true", help="仅预览分析")
    parser.add_argument("--json", action="store_true", help="JSON输出")
    parser.add_argument("--serve", action="store_true", help="启动HTTP服务")
    parser.add_argument("--port", type=int, default=8080, help="HTTP端口")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # 处理列出预设的命令
    if args.list_luts or args.list_tones:
        from core.color_grade import ColorGrader
        grader = ColorGrader()
        
        if args.list_tones:
            presets = grader.list_presets()
            print("\n🎨 可用调色预设:")
            for name, info in presets.items():
                preset_type = info.get("type", "unknown")
                desc = info.get("description", "")
                if preset_type == "lut":
                    print(f"  {name} [LUT]: {desc}")
                else:
                    print(f"  {name}: {desc}")
        
        if args.list_luts:
            luts = grader.list_lut_presets()
            print("\n🎬 可用LUT预设:")
            if luts:
                for lut in luts:
                    print(f"  {lut['name']}: {lut['description']}")
            else:
                print("  未找到LUT文件，请将.cube文件放入assets/luts/目录")
        
        return

    if args.serve:
        try:
            from fastapi import FastAPI
            import uvicorn
            from skill import SOEAutoEditSkill

            app = FastAPI(title="SOE Auto Editor API", version="1.0.0")
            skill = SOEAutoEditSkill()

            @app.post("/api/v1/edit")
            async def edit(req: dict):
                result = await skill.execute(req)
                return result

            @app.get("/api/v1/health")
            async def health():
                return {"status": "ok"}

            print(f"  SOE Auto Editor API → http://localhost:{args.port}")
            uvicorn.run(app, host="0.0.0.0", port=args.port)
        except ImportError:
            print("FastAPI 未安装，运行: pip install fastapi uvicorn")
            sys.exit(1)
        return

    if not args.videos:
        parser.print_help()
        return

    from skill import SOEAutoEditSkill
    skill = SOEAutoEditSkill()

    if args.preview:
        result = asyncio.run(skill.preview({
            "input_videos": args.videos,
            "template": args.template,
        }))
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"\n  预览分析: {args.template}")
            print(f"  总场景: {result['total_scenes']}个")
            print(f"  总时长: {result['total_duration']:.1f}秒")
            print(f"\n  分类分布:")
            for cat, info in result.get("category_distribution", {}).items():
                print(f"    {cat}: {info['count']}个, {info['total_duration']:.1f}秒")
            print()
    else:
        print(f"\n  SOE Auto Editor v1.0")
        print(f"  模板: {args.template}")
        print(f"  输入: {len(args.videos)}个视频\n")

        # 确定调色预设
        color_tone = args.tone
        if args.lut:
            color_tone = args.lut
        
        result = skill.edit_sync(
            input_videos=args.videos,
            template=args.template,
            title=args.title,
            subtitle=args.subtitle,
            organization=args.org,
            date_text=args.date,
            target_duration=args.duration,
            music_path=args.music,
            output_path=args.output,
            logo_path=args.logo,
            color_tone=color_tone,
        )

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif result["success"]:
            print(f"  ✅ 剪辑完成!")
            print(f"  输出: {result['output_path']}")
            print(f"  时长: {result['duration']:.1f}秒")
            print(f"  场景: {result['scenes_selected']}/{result['scenes_detected']}个")
            print(f"  音乐: {result['music_used']}")
            elapsed = result.get("metadata", {}).get("elapsed", 0)
            print(f"  用时: {elapsed:.1f}秒\n")
        else:
            print(f"  ❌ 剪辑失败: {result['error']}\n")
            sys.exit(1)


if __name__ == "__main__":
    main()
