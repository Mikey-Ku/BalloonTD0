import numpy as np
import csv

# Define the given points
points = [
    (0.0, 250),
    (400, 250),
    (400, 110),
    (265, 110),
    (265, 480),
    (135, 480),
    (135, 350),
    (510, 350),
    (510, 195),
    (605, 195),
    (605, 430),
    (360, 430),
    (360, 490),
    (360, 600),
]


# Function to calculate the distance between two points
def distance(p1, p2):
    return np.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)


# Calculate the total length of the path
total_length = sum(
    distance(points[i], points[i + 1]) for i in range(len(points) - 1)
)

# Calculate the step size for 2500 equidistant points
step_size = total_length / 2499  # 2499 steps between 2500 points

# Generate the equidistant points
equidistant_points = [points[0]]
current_point = points[0]
remaining_distance = step_size

for i in range(len(points) - 1):
    p1, p2 = points[i], points[i + 1]
    segment_length = distance(p1, p2)
    direction = (
        (p2[0] - p1[0]) / segment_length,
        (p2[1] - p1[1]) / segment_length,
    )

    while remaining_distance <= segment_length:
        current_point = (
            current_point[0] + direction[0] * remaining_distance,
            current_point[1] + direction[1] * remaining_distance,
        )
        equidistant_points.append(current_point)
        segment_length -= remaining_distance
        remaining_distance = step_size

    current_point = p2
    remaining_distance -= segment_length

# Save the points to a CSV file
with open("equidistant_points.csv", "w", newline="") as csvfile:
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(["x", "y"])
    csvwriter.writerows(equidistant_points)

print("CSV file 'equidistant_points.csv' has been created.")
