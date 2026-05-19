"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import numpy as np
import pyray as rl

from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight, FONT_SCALE
from openpilot.system.ui.lib.text_measure import measure_text_cached

# Distance-based colors: close = red/orange, far = green
DIST_CLOSE = 15.0   # m — red below this
DIST_MID = 40.0     # m — orange between close and mid
# above mid = green

COLOR_CLOSE = (255, 60, 60)
COLOR_MID_C = (255, 180, 0)
COLOR_FAR = (0, 255, 64)

ICON_SIZE = 40
PILL_W = 56
PILL_H = 84
BORDER_W = 3
FONT_SIZE = 22


class LeadCarIndicator:
  def __init__(self):
    self._lead_status_alpha: float = 0.0
    self._dist_filter = FirstOrderFilter(50.0, 0.5, 1 / gui_app.target_fps)
    self._car_icon = gui_app.texture("../../sunnypilot/selfdrive/assets/offroad/icon_vehicle.png", ICON_SIZE, ICON_SIZE)
    self._font = gui_app.font(FontWeight.SEMI_BOLD)
    # last known values — held during fade-out so pill stays coherent
    self._last_d_rel: float = 50.0
    self._last_color: tuple[int, int, int] = COLOR_FAR

  def _update_alpha(self, has_lead: bool):
    if not has_lead:
      self._lead_status_alpha = max(0.0, self._lead_status_alpha - 0.05)
    else:
      self._lead_status_alpha = min(1.0, self._lead_status_alpha + 0.1)

  @staticmethod
  def _dist_color(d: float) -> tuple[int, int, int]:
    if d <= DIST_CLOSE:
      return COLOR_CLOSE
    if d <= DIST_MID:
      return COLOR_MID_C
    return COLOR_FAR

  def _draw_pill(self, cx: float, cy: float, color: tuple[int, int, int],
                 d_rel: float, alpha: float) -> None:
    a = int(255 * alpha)
    half_w = PILL_W / 2
    half_h = PILL_H / 2

    pill = rl.Rectangle(cx - half_w, cy - half_h, PILL_W, PILL_H)

    # Dark background
    rl.draw_rectangle_rounded(pill, 0.35, 12, rl.Color(0, 0, 0, int(a * 0.75)))

    # Colored border
    rl.draw_rectangle_rounded_lines_ex(pill, 0.35, 12, BORDER_W,
                                       rl.Color(color[0], color[1], color[2], a))

    # Car icon — white, centered in upper portion of pill
    icon_x = cx - ICON_SIZE / 2
    icon_y = cy - half_h + 8
    rl.draw_texture_ex(self._car_icon, rl.Vector2(icon_x, icon_y), 0.0, 1.0,
                       rl.Color(255, 255, 255, a))

    # Distance text below icon
    val = max(0.0, d_rel)
    unit = "m" if ui_state.is_metric else "ft"
    if not ui_state.is_metric:
      val *= 3.28084
    text = f"{val:.0f}{unit}"

    measure = measure_text_cached(self._font, text, FONT_SIZE, 0)
    text_x = cx - measure.x / 2
    text_y = cy + half_h - measure.y * FONT_SCALE - 8
    rl.draw_text_ex(self._font, text, rl.Vector2(text_x, text_y),
                    FONT_SIZE, 0, rl.Color(color[0], color[1], color[2], a))

  def draw_lead_car(self, sm, radar_state, rect: rl.Rectangle, lead_vehicles) -> None:
    pass

  def draw_in_panel(self, panel_rect: rl.Rectangle, radar_state) -> bool:
    """Draw lead indicator pill in the side panel. Returns True while visible (incl. fade-out)."""
    lead_one = radar_state.leadOne if radar_state else None
    has_lead = bool(lead_one and lead_one.status)

    self._update_alpha(has_lead)

    if self._lead_status_alpha <= 0.0:
      return False

    # Update live values only while lead is present; hold last values during fade-out
    if has_lead:
      d_rel = float(lead_one.dRel)
      self._dist_filter.update(d_rel)
      self._last_d_rel = d_rel
      self._last_color = self._dist_color(d_rel)

    smoothed_dist = self._dist_filter.x
    cx = panel_rect.x + panel_rect.width / 2

    # Close lead = top of panel, far lead = bottom
    margin = PILL_H / 2 + 6
    cy = float(np.interp(smoothed_dist, [0.0, 100.0],
                         [panel_rect.y + margin, panel_rect.y + panel_rect.height - margin]))

    self._draw_pill(cx, cy, self._last_color, self._last_d_rel, self._lead_status_alpha)
    return True
