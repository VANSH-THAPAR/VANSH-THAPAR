import os
import re
import math
import time
import config
from datetime import date
from dateutil.relativedelta import relativedelta
from utils import calculate_age, setup_logger

logger = setup_logger(__name__)

class LayoutConstants:
    CANVAS_WIDTH = 1600
    CANVAS_HEIGHT = 1200
    
    # Portrait
    PORTRAIT_X = 40
    PORTRAIT_Y = 110
    PORTRAIT_WIDTH = 420
    PORTRAIT_HEIGHT = 420
    
    # Profile
    PROFILE_X = 500
    PROFILE_Y = 70
    PROFILE_WIDTH = 1060
    
    # GitHub
    GITHUB_X = 40
    GITHUB_Y = 580
    GITHUB_WIDTH = 1520
    
    # LeetCode
    LC_X = 40
    LC_Y = 800
    LC_WIDTH = 1520
    
    # Font Settings
    LINE_HEIGHT = 26
    CHAR_WIDTH = 9.5
    FONT_SIZE = 16

class SVGTextBuilder:
    def __init__(self, x=0, y=0, max_width=1000, line_height=26, char_width=9.5):
        self.x = x
        self.y = y
        self.max_width = max_width
        self.line_height = line_height
        self.char_width = char_width
        self.lines = []
        
    def add_line(self, content):
        self.y += self.line_height
        self.lines.append(f'<tspan x="{self.x}" y="{self.y}">{content}</tspan>')
        
    def add_empty_line(self):
        self.y += self.line_height

    def build(self):
        return "\n".join(self.lines)

    def kv_line(self, key, value, indent=20, is_last=False, is_string=True, value_class="string"):
        comma = "" if is_last else ","
        val_str = f'"{value}"' if is_string else str(value)
        
        # Simple truncation for extremely long values
        max_chars = int((self.max_width - indent - len(key) - 10) / self.char_width)
        if len(val_str) > max_chars and max_chars > 3:
            val_str = val_str[:max_chars-3] + "..."
            if is_string:
                val_str += '"'
                
        return f'<tspan x="{self.x + indent}" class="keyword">"{key}"</tspan><tspan class="text">: </tspan><tspan class="{value_class}">{val_str}</tspan><tspan class="text">{comma}</tspan>'

    def wrap_array(self, key, items, indent=20, is_last=False):
        lines = []
        lines.append(f'<tspan x="{self.x + indent}" class="keyword">"{key}"</tspan><tspan class="text">: [</tspan>')
        
        max_chars = int((self.max_width - indent - 40) / self.char_width)
        
        current_line = []
        current_len = 0
        chunks = []
        for item in items:
            if current_len + len(item) + 4 > max_chars and current_line:
                chunks.append(current_line)
                current_line = [item]
                current_len = len(item)
            else:
                current_line.append(item)
                current_len += len(item) + 4
                
        if current_line:
            chunks.append(current_line)
            
        for i, chunk in enumerate(chunks):
            chunk_str = '"' + '", "'.join(chunk) + '"'
            if i < len(chunks) - 1:
                chunk_str += ","
            lines.append(f'<tspan x="{self.x + indent + 20}" class="value">{chunk_str}</tspan>')
            
        comma = "" if is_last else ","
        lines.append(f'<tspan x="{self.x + indent}" class="text">]{comma}</tspan>')
        return lines


class ProfileRenderer:
    def __init__(self, template_path: str, portrait_path: str = None):
        self.template_path = template_path
        self.portrait_path = portrait_path
        self.template_content = ""
        self.portrait_content = ""
        self.load_files()

    def load_files(self):
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                self.template_content = f.read()
            if self.portrait_path and os.path.exists(self.portrait_path):
                with open(self.portrait_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    content = re.sub(r'<\?xml.*?\?>', '', content)
                    content = re.sub(r'<!DOCTYPE.*?>', '', content)
                    self.portrait_content = content.strip()
        except Exception as e:
            logger.error(f"Failed to load SVG files: {e}")
            raise

    def render_portrait(self):
        if not self.portrait_path or not self.portrait_content:
            return ""
            
        try:
            import xml.etree.ElementTree as ET
            
            tree = ET.fromstring(self.portrait_content)
            
            viewbox = tree.get('viewBox')
            width = tree.get('width')
            height = tree.get('height')
            
            orig_w, orig_h = 0.0, 0.0
            
            if viewbox:
                parts = viewbox.split()
                if len(parts) >= 4:
                    orig_w = float(parts[2])
                    orig_h = float(parts[3])
            
            if orig_w == 0.0 and width:
                orig_w = float(width.replace('px', '').replace('%', ''))
            if orig_h == 0.0 and height:
                orig_h = float(height.replace('px', '').replace('%', ''))
                
            if orig_w == 0.0:
                orig_w = 1254.0 # fallback
            if orig_h == 0.0:
                orig_h = 1254.0
                
            scale = LayoutConstants.PORTRAIT_WIDTH / orig_w
            
            logger.info(f"Original portrait size: {orig_w}x{orig_h}")
            logger.info(f"Calculated scale: {scale}")
            
            num_children = len(list(tree))
            ns = ''
            m = re.match(r'\{.*\}', tree.tag)
            if m:
                ns = m.group(0)
            num_defs = len(tree.findall(f'.//{ns}defs'))
            
            logger.info(f"Number of root children imported: {num_children}")
            logger.info(f"Number of defs imported: {num_defs}")
            
            match = re.search(r'<svg[^>]*>', self.portrait_content)
            if match:
                start_idx = match.end()
                end_idx = self.portrait_content.rfind('</svg>')
                if end_idx != -1:
                    inner_content = self.portrait_content[start_idx:end_idx].strip()
                    
                    prompt_y = LayoutConstants.PORTRAIT_Y - 15
                    prompt_svg = f'<text x="{LayoutConstants.PORTRAIT_X}" y="{prompt_y}" class="text"><tspan class="prompt">vansh@thapar:~$</tspan> neofetch</text>'
                    
                    g_start = f'<g transform="translate({LayoutConstants.PORTRAIT_X},{LayoutConstants.PORTRAIT_Y}) scale({scale})">'
                    g_end = '</g>'
                    
                    return f"{prompt_svg}\n{g_start}\n{inner_content}\n{g_end}"
                    
        except Exception as e:
            logger.error(f"Failed to process portrait.svg: {e}")
            
        return ""

    def render_profile_panel(self, github_stats):
        builder = SVGTextBuilder(
            x=LayoutConstants.PROFILE_X, 
            y=LayoutConstants.PROFILE_Y, 
            max_width=LayoutConstants.PROFILE_WIDTH,
            line_height=LayoutConstants.LINE_HEIGHT,
            char_width=LayoutConstants.CHAR_WIDTH
        )
        
        # whoami
        builder.add_line('<tspan class="prompt">vansh@thapar:~$</tspan><tspan class="text"> whoami</tspan>')
        builder.add_line(f'<tspan class="value">{config.NAME}</tspan>')
        builder.add_line(f'<tspan class="text">{config.OCCUPATION}</tspan>')
        builder.add_line(f'<tspan class="text">{config.DEGREE}</tspan>')
        builder.add_line(f'<tspan class="text">{config.COUNTRY}</tspan>')
        builder.add_empty_line()
        
        # uptime
        builder.add_line('<tspan class="prompt">vansh@thapar:~$</tspan><tspan class="text"> uptime</tspan>')
        builder.add_line(f'<tspan class="value">{calculate_age()}</tspan>')
        builder.add_empty_line()
        
        # JSON Profile
        builder.add_line('<tspan class="prompt">vansh@thapar:~$</tspan><tspan class="text"> cat profile.json</tspan>')
        builder.add_line('<tspan class="text">{</tspan>')
        builder.add_line(builder.kv_line("whoami", config.NAME))
        builder.add_line(builder.kv_line("kernel", "Windows NT + WSL2"))
        builder.add_line(builder.kv_line("shell", "PowerShell"))
        builder.add_line(builder.kv_line("workspace", "Full Stack + AI"))
        
        for line in builder.wrap_array("languages", config.PROGRAMMING_LANGUAGES):
            builder.add_line(line)
            
        for line in builder.wrap_array("currently_learning", ["Spark", "BigQuery", "Airflow"]):
            builder.add_line(line)
            
        builder.add_line(builder.kv_line("status", "Building AI products.", is_last=True))
        builder.add_line('<tspan class="text">}</tspan>')
        
        return f'<text class="text">\n{builder.build()}\n</text>'
        
    def render_github_panel(self, github_stats):
        builder = SVGTextBuilder(x=LayoutConstants.GITHUB_X, y=LayoutConstants.GITHUB_Y, max_width=LayoutConstants.GITHUB_WIDTH)
        builder.add_line('<tspan class="prompt">vansh@thapar:~$</tspan><tspan class="text"> github</tspan>')
        text_svg = f'<text class="text">\n{builder.build()}\n</text>'
        
        card_y = builder.y + 20
        spacing = 20
        num_cards = 5
        card_w = (LayoutConstants.GITHUB_WIDTH - spacing * (num_cards - 1)) / num_cards
        card_h = 100
        
        cards = [
            ("Followers", github_stats.get('FOLLOWERS', 0), "★", "Community"),
            ("Repositories", github_stats.get('REPOS', 0), "📁", "Public Projects"),
            ("Stars", github_stats.get('STARS', 0), "⭐", "Received"),
            ("Commits", github_stats.get('COMMITS', 0), "🔨", "Total"),
            ("Contributions", github_stats.get('CONTRIBUTIONS', 0), "🔥", "This Year")
        ]
        
        svg_parts = [text_svg]
        
        for i, (title, value, icon, subtitle) in enumerate(cards):
            cx = LayoutConstants.GITHUB_X + i * (card_w + spacing)
            svg_parts.append(f'<rect x="{cx}" y="{card_y}" width="{card_w}" height="{card_h}" rx="12" fill="{{{{TITLE_BAR_BG}}}}" class="border" />')
            svg_parts.append(f'<text x="{cx + 20}" y="{card_y + 40}" font-size="24">{icon}</text>')
            svg_parts.append(f'<text x="{cx + 55}" y="{card_y + 35}" class="text keyword" font-size="16">{title}</text>')
            svg_parts.append(f'<text x="{cx + 55}" y="{card_y + 80}" class="text value" font-size="32" font-weight="bold">{value}</text>')
            svg_parts.append(f'<text x="{cx + card_w - 20}" y="{card_y + 80}" class="text" font-size="14" text-anchor="end" opacity="0.6">{subtitle}</text>')
            
        return "\n".join(svg_parts)

    def render_heatmap(self, cal_data, start_x, start_y, max_width):
        if not cal_data:
            return f'<text x="{start_x + (max_width/2)}" y="{start_y + 40}" class="text keyword" font-size="16" text-anchor="middle">No LeetCode submission data available</text>'
            
        box_size = 14
        gap = 4
        rows = 7
        cols = 52
        
        heatmap_width = cols * (box_size + gap)
        # Center horizontally in the allocated space
        offset_x = start_x + (max_width - heatmap_width) / 2
        
        now = time.time()
        start_time = now - (cols * 7 * 86400)
        
        svg_rects = []
        for col in range(cols):
            for row in range(rows):
                day_offset = (col * 7 + row)
                target_time = start_time + (day_offset * 86400)
                
                count = 0
                for ts, c in cal_data.items():
                    if abs(int(ts) - target_time) < 86400:
                        count += c
                        
                level = 0
                if count > 10: level = 4
                elif count > 5: level = 3
                elif count > 2: level = 2
                elif count > 0: level = 1
                
                level_var = f"{{{{LC_HEATMAP_L{level}}}}}"
                
                x_pos = offset_x + col * (box_size + gap)
                y_pos = start_y + row * (box_size + gap)
                
                svg_rects.append(f'<rect x="{x_pos}" y="{y_pos}" width="{box_size}" height="{box_size}" rx="3" fill="{level_var}" />')
        
        # Add legend
        legend_y = start_y + rows * (box_size + gap) + 15
        legend_x = offset_x + heatmap_width - 150
        svg_rects.append(f'<text x="{legend_x - 45}" y="{legend_y + 11}" class="text" font-size="12">Less</text>')
        for i in range(5):
            lx = legend_x + i * (box_size + gap)
            level_var = f"{{{{LC_HEATMAP_L{i}}}}}"
            svg_rects.append(f'<rect x="{lx}" y="{legend_y}" width="{box_size}" height="{box_size}" rx="2" fill="{level_var}" />')
        svg_rects.append(f'<text x="{legend_x + 5 * (box_size + gap) + 10}" y="{legend_y + 11}" class="text" font-size="12">More</text>')
                
        return "\n".join(svg_rects)

    def render_leetcode_panel(self, lc_stats):
        builder = SVGTextBuilder(
            x=LayoutConstants.LC_X,
            y=LayoutConstants.LC_Y,
            max_width=LayoutConstants.LC_WIDTH,
            line_height=LayoutConstants.LINE_HEIGHT,
            char_width=LayoutConstants.CHAR_WIDTH
        )
        
        builder.add_line('<tspan class="prompt">vansh@thapar:~$</tspan><tspan class="text"> leetcode</tspan>')
        text_svg = f'<text class="text">\n{builder.build()}\n</text>'
        
        start_y = builder.y + 20
        svg_parts = [text_svg]
        
        bar_w = 400
        cx = LayoutConstants.LC_X
        
        svg_parts.append(f'<text x="{cx}" y="{start_y + 20}" class="text keyword">Username:</text>')
        svg_parts.append(f'<text x="{cx + 100}" y="{start_y + 20}" class="text value">{config.LEETCODE_USERNAME}</text>')
        
        svg_parts.append(f'<text x="{cx}" y="{start_y + 50}" class="text keyword">Global Rank:</text>')
        svg_parts.append(f'<text x="{cx + 130}" y="{start_y + 50}" class="text value">{lc_stats.get("LC_RANKING", "N/A")}</text>')

        svg_parts.append(f'<text x="{cx}" y="{start_y + 80}" class="text keyword">Contest Rating:</text>')
        svg_parts.append(f'<text x="{cx + 160}" y="{start_y + 80}" class="text value">{lc_stats.get("LC_RATING", "N/A")}</text>')

        bx = cx + 400
        easy = int(lc_stats.get('LC_EASY', 0))
        med = int(lc_stats.get('LC_MEDIUM', 0))
        hard = int(lc_stats.get('LC_HARD', 0))
        total = int(lc_stats.get('LC_SOLVED', 0))
        
        def draw_bar(y, label, val, total_val, color):
            pct = (val / max(1, total_val)) * bar_w
            return [
                f'<text x="{bx}" y="{y}" class="text" font-size="14">{label}</text>',
                f'<text x="{bx + bar_w}" y="{y}" class="text value" font-size="14" text-anchor="end">{val}</text>',
                f'<rect x="{bx}" y="{y + 10}" width="{bar_w}" height="8" rx="4" fill="{{{{TITLE_BAR_BG}}}}" />',
                f'<rect x="{bx}" y="{y + 10}" width="{pct}" height="8" rx="4" fill="{color}" />'
            ]
            
        svg_parts.extend(draw_bar(start_y, "Easy", easy, total, "#28a745"))
        svg_parts.extend(draw_bar(start_y + 40, "Medium", med, total, "#ffc107"))
        svg_parts.extend(draw_bar(start_y + 80, "Hard", hard, total, "#dc3545"))
        
        heatmap_start_y = start_y + 120
        cal_data = lc_stats.get("LC_CALENDAR", {})
        heatmap_svg = self.render_heatmap(cal_data, LayoutConstants.LC_X, heatmap_start_y, LayoutConstants.LC_WIDTH)
        svg_parts.append(heatmap_svg)
        
        return "\n".join(svg_parts)

    def render(self, output_path: str, theme_name: str, github_stats: dict, leetcode_stats: dict):
        content = self.template_content
        
        required_placeholders = ["{{PORTRAIT}}", "{{PROFILE}}", "{{GITHUB}}", "{{LEETCODE}}"]
        for p in required_placeholders:
            if p not in content:
                raise ValueError(f"CRITICAL ERROR: Placeholder {p} is missing from template.svg!")
                
        theme = config.THEMES.get(theme_name, config.THEMES["dark"])
        for k, v in theme.items():
            content = content.replace(f"{{{{{k.upper()}}}}}", v)
            
        if theme_name == "dark":
            content = content.replace("{{LC_HEATMAP_L0}}", theme.get("border_color", "#30363d"))
            content = content.replace("{{LC_HEATMAP_L1}}", "#0e4429")
            content = content.replace("{{LC_HEATMAP_L2}}", "#006d32")
            content = content.replace("{{LC_HEATMAP_L3}}", "#26a641")
            content = content.replace("{{LC_HEATMAP_L4}}", "#39d353")
        else:
            content = content.replace("{{LC_HEATMAP_L0}}", "#ebedf0")
            content = content.replace("{{LC_HEATMAP_L1}}", "#9be9a8")
            content = content.replace("{{LC_HEATMAP_L2}}", "#40c463")
            content = content.replace("{{LC_HEATMAP_L3}}", "#30a14e")
            content = content.replace("{{LC_HEATMAP_L4}}", "#216e39")
            
        placeholders = {
            "{{PORTRAIT}}": self.render_portrait(),
            "{{PROFILE}}": self.render_profile_panel(github_stats),
            "{{GITHUB}}": self.render_github_panel(github_stats),
            "{{LEETCODE}}": self.render_leetcode_panel(leetcode_stats)
        }
        
        for k, v in placeholders.items():
            content = content.replace(k, str(v))
            
        logger.info(f"Placeholder replacement success for {theme_name} mode.")
            
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Final output path: {output_path}")
        except Exception as e:
            logger.error(f"Failed to write SVG to {output_path}: {e}")
