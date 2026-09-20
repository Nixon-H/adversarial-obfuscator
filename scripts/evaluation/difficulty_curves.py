import math


class DifficultyCurveAnalyzer:
    """
    Measures how reverse engineering difficulty scales with protection intensity.

    Sweeps protection parameters (MBA depth, CFG flattening, fragment count)
    and produces difficulty curves: protection_intensity vs estimated_RE_hours.

    Fits curve: hours = a * intensity^b + c
    """

    def __init__(self):
        self._curves = {}

    def analyze(self, protection_metrics: dict) -> dict:
        curves = {}
        curves['mba_depth'] = self._build_mba_depth_curve(protection_metrics)
        curves['cfg_flattening'] = self._build_cfg_flattening_curve(protection_metrics)
        curves['fragment_count'] = self._build_fragment_count_curve(protection_metrics)
        curves['overall'] = self._build_overall_curve(protection_metrics)
        self._curves = curves
        return curves

    def _build_mba_depth_curve(self, metrics: dict) -> dict:
        points = []
        max_depth = metrics.get('protected_mba_depth', 10)
        if isinstance(metrics.get('symbolic_resistance'), dict):
            max_depth = metrics['symbolic_resistance'].get('protected_mba_depth', max_depth)
        for depth in range(0, max_depth + 1):
            hours = self._mba_hours(depth)
            points.append({'intensity': depth, 'estimated_hours': round(hours, 2)})
        params = self._fit_curve(points)
        inflection = self._find_inflection(points)
        return {
            'points': points,
            'curve_parameters': params,
            'inflection_point': inflection,
            'max_depth': max_depth,
        }

    def _build_cfg_flattening_curve(self, metrics: dict) -> dict:
        points = []
        max_blocks = metrics.get('protected_blocks', 50)
        if isinstance(metrics.get('cfg_entropy'), dict):
            max_blocks = metrics['cfg_entropy'].get('protected_blocks', max_blocks)
        step = max(1, max_blocks // 10)
        for blocks in range(0, max_blocks + 1, step):
            hours = self._cfg_hours(blocks)
            points.append({'intensity': blocks, 'estimated_hours': round(hours, 2)})
        params = self._fit_curve(points)
        inflection = self._find_inflection(points)
        return {
            'points': points,
            'curve_parameters': params,
            'inflection_point': inflection,
            'max_blocks': max_blocks,
        }

    def _build_fragment_count_curve(self, metrics: dict) -> dict:
        points = []
        max_fragments = metrics.get('fragment_count', 20)
        for count in range(0, max_fragments + 1):
            hours = self._fragment_hours(count)
            points.append({'intensity': count, 'estimated_hours': round(hours, 2)})
        params = self._fit_curve(points)
        inflection = self._find_inflection(points)
        return {
            'points': points,
            'curve_parameters': params,
            'inflection_point': inflection,
            'max_fragments': max_fragments,
        }

    def _build_overall_curve(self, metrics: dict) -> dict:
        points = []
        max_depth = metrics.get('protected_mba_depth', 10)
        if isinstance(metrics.get('symbolic_resistance'), dict):
            max_depth = metrics['symbolic_resistance'].get('protected_mba_depth', max_depth)
        max_blocks = metrics.get('protected_blocks', 50)
        if isinstance(metrics.get('cfg_entropy'), dict):
            max_blocks = metrics['cfg_entropy'].get('protected_blocks', max_blocks)
        max_fragments = metrics.get('fragment_count', 20)
        combined_max = max(1, max_depth + max_blocks // 10 + max_fragments)
        step = max(1, combined_max // 15)
        for intensity in range(0, combined_max + 1, step):
            hours = (
                self._mba_hours(intensity * max_depth // max(combined_max, 1))
                + self._cfg_hours(intensity * max_blocks // max(combined_max, 1))
                + self._fragment_hours(intensity * max_fragments // max(combined_max, 1))
            )
            points.append({'intensity': intensity, 'estimated_hours': round(hours, 2)})
        params = self._fit_curve(points)
        inflection = self._find_inflection(points)
        return {
            'points': points,
            'curve_parameters': params,
            'inflection_point': inflection,
        }

    @staticmethod
    def _mba_hours(depth: int) -> float:
        return 2.0 * (depth ** 1.5) + 1.0

    @staticmethod
    def _cfg_hours(blocks: int) -> float:
        return 0.5 * (blocks ** 1.3) + 0.5

    @staticmethod
    def _fragment_hours(count: int) -> float:
        return 3.0 * (count ** 1.2) + 2.0

    @staticmethod
    def _fit_curve(points: list) -> dict:
        if len(points) < 3:
            return {'a': 0, 'b': 1, 'c': 0, 'r_squared': 0}
        x_vals = [p['intensity'] for p in points if p['intensity'] > 0]
        y_vals = [p['estimated_hours'] for p in points if p['intensity'] > 0]
        if not x_vals or not y_vals:
            return {'a': 0, 'b': 1, 'c': 0, 'r_squared': 0}
        log_x = [math.log(max(x, 1)) for x in x_vals]
        log_y = [math.log(max(y, 0.001)) for y in y_vals]
        n = len(x_vals)
        sx = sum(log_x)
        sy = sum(log_y)
        sxx = sum(x * x for x in log_x)
        sxy = sum(log_x[i] * log_y[i] for i in range(n))
        b = (n * sxy - sx * sy) / max(n * sxx - sx * sx, 0.001)
        log_a = (sy - b * sx) / n
        a = math.exp(log_a)
        c = min(y_vals) * 0.1
        y_mean = sum(y_vals) / n
        ss_res = sum((y - (a * (x ** b) + c)) ** 2 for x, y in zip(x_vals, y_vals))
        ss_tot = sum((y - y_mean) ** 2 for y in y_vals)
        r_sq = 1.0 - (ss_res / max(ss_tot, 0.001))
        return {
            'a': round(a, 4),
            'b': round(b, 4),
            'c': round(c, 4),
            'r_squared': round(r_sq, 4),
        }

    @staticmethod
    def _find_inflection(points: list) -> dict:
        if len(points) < 3:
            return {'exists': False, 'intensity': None, 'hours': None}
        max_derivative = 0.0
        inflection_idx = 0
        for i in range(1, len(points)):
            dx = points[i]['intensity'] - points[i - 1]['intensity']
            dy = points[i]['estimated_hours'] - points[i - 1]['estimated_hours']
            if dx > 0:
                derivative = dy / dx
                if derivative > max_derivative:
                    max_derivative = derivative
                    inflection_idx = i
        return {
            'exists': max_derivative > 0,
            'intensity': points[inflection_idx]['intensity'],
            'hours': points[inflection_idx]['estimated_hours'],
            'max_derivative': round(max_derivative, 4),
        }
