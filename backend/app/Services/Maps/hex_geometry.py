# backend/app/Services/Maps/hex_geometry.py

"""Чистая геометрия гекс-сетки: координаты axial/cube, соседи, дистанция, линия видимости."""

AXIAL_DIRECTIONS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]

def axial_to_cube(q: int, r: int) -> tuple[int, int, int]:
	return q, -q - r, r

def cube_to_axial(cube: tuple[float, float, float]) -> tuple[int, int]:
	return round(cube[0]), round(cube[2])

def cube_distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> int:
	return int((abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])) / 2)

def axial_distance(a: tuple[int, int], b: tuple[int, int]) -> int:
	return cube_distance(axial_to_cube(*a), axial_to_cube(*b))

def axial_neighbors(q: int, r: int) -> list[tuple[int, int]]:
	return [(q + dq, r + dr) for dq, dr in AXIAL_DIRECTIONS]

def offset_to_axial_oddr(col: int, row: int) -> tuple[int, int]:
	"""Стандартная формула offset→axial для нечётных строк (pointy-top, odd-r)."""
	q = col - (row - (row & 1)) // 2
	r = row
	return q, r

def _cube_round(cube: tuple[float, float, float]) -> tuple[int, int, int]:
	rx, ry, rz = round(cube[0]), round(cube[1]), round(cube[2])
	dx, dy, dz = abs(rx - cube[0]), abs(ry - cube[1]), abs(rz - cube[2])
	if dx > dy and dx > dz:
		rx = -ry - rz
	elif dy > dz:
		ry = -rx - rz
	else:
		rz = -rx - ry
	return rx, ry, rz

def hex_line_draw(a: tuple[int, int], b: tuple[int, int]) -> list[tuple[int, int]]:
	"""Все гексы (axial) на прямой между a и b, включая концы."""
	cube_a = axial_to_cube(*a)
	cube_b = axial_to_cube(*b)
	distance = cube_distance(cube_a, cube_b)
	if distance == 0:
		return [a]
	points = []
	for step in range(distance + 1):
		t = step / distance
		lerp = tuple(cube_a[i] + (cube_b[i] - cube_a[i]) * t for i in range(3))
		points.append(cube_to_axial(_cube_round(lerp)))
	return points