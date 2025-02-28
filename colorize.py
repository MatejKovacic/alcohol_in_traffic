import re  # Import the regex module
import argparse
import pandas as pd
import matplotlib.colors as mcolors

# Static SVG file path
SVG_FILE_PATH = "administrative-units.svg"  # Update this if the file is in a different location

# Function to process the CSV and SVG files
def process_files(csv_file_path, title):
    # Load the CSV accident data
    df = pd.read_csv(csv_file_path)  # Read the CSV file with headers
    df.columns = ["unit_id", "accidents"]  # Rename columns for consistency

    # Ensure the accidents column is numeric
    df["accidents"] = pd.to_numeric(df["accidents"], errors="coerce")

    # Load the SVG file
    with open(SVG_FILE_PATH, "r", encoding="utf-8") as file:
        svg_content = file.read()

    # Define a function to assign colors based on accident counts
    def get_color(accidents, min_val, max_val):
        norm = (accidents - min_val) / (max_val - min_val)  # Normalize to 0-1
        cmap = mcolors.LinearSegmentedColormap.from_list("accident_scale", ["lightblue", "darkblue"])
        return mcolors.rgb2hex(cmap(norm))  # Convert to hex color

    # Determine min/max accidents for scaling
    min_accidents = df["accidents"].min()
    max_accidents = df["accidents"].max()

    # Update the SVG file with color-coded regions
    for _, row in df.iterrows():
        unit_id = row["unit_id"]  # Example: UE-01
        accidents = row["accidents"]
        color = get_color(accidents, min_accidents, max_accidents)  # Get color

        # Apply color to paths with matching IDs
        svg_content = re.sub(
            f'(<path[^>]*id="{unit_id}"[^>]*)(fill="[^"]*"|)',  # Match the path with the correct ID
            rf'\1 fill="{color}"',  # Apply the new color
            svg_content
        )

    # Add a title to the SVG
    title_x = 70  # Fixed position from the left margin
    title_y = 30  # Y position of the title (top of the map)
    title_text = f'<text x="{title_x}" y="{title_y}" font-family="Trebuchet MS" font-size="32" font-weight="bold">{title}</text>'

    # Add a legend to the SVG
    legend_x = 800  # X position of the legend (left side)
    legend_y = 600  # Y position of the legend (bottom side)
    legend_width = 200  # Width of the legend
    legend_height = 20  # Height of each color bar
    num_steps = 5  # Number of steps in the legend

    # Create the legend gradient
    legend_gradient = f'<defs>\
        <linearGradient id="legendGradient" x1="0%" y1="0%" x2="100%" y2="0%">\
        <stop offset="0%" style="stop-color:lightblue;stop-opacity:1" />\
        <stop offset="100%" style="stop-color:darkblue;stop-opacity:1" />\
        </linearGradient>\
        </defs>'

    # Create the legend rectangle
    legend_rect = f'<rect x="{legend_x}" y="{legend_y}" width="{legend_width}" height="{legend_height}" fill="url(#legendGradient)" />'

    # Add "LEGEND:" label above the legend
    legend_label = f'<text x="{legend_x}" y="{legend_y - 10}" font-family="Trebuchet MS" font-size="16" font-weight="bold">Legend:</text>'

    # Add labels to the legend
    legend_labels = ""
    for i in range(num_steps + 1):
        value = min_accidents + (max_accidents - min_accidents) * (i / num_steps)
        label_x = legend_x + (legend_width * (i / num_steps))
        legend_labels += f'<text x="{label_x}" y="{legend_y + legend_height + 20}" font-family="Trebuchet MS" font-size="10" text-anchor="middle">{int(value)}</text>'

    # Add additional text under the legend
    legend_subtext = f'<text x="{legend_x}" y="{legend_y + legend_height + 40}" font-family="Trebuchet MS" font-size="11">(absolute number)</text>'

    # Combine legend elements
    legend = f'{legend_gradient}{legend_rect}{legend_label}{legend_labels}{legend_subtext}'

    # Insert the title and legend into the SVG content
    svg_content = svg_content.replace("</svg>", f'{title_text}{legend}</svg>')

    # Save the updated SVG
    output_svg_path = csv_file_path.replace(".csv", ".svg")
    with open(output_svg_path, "w", encoding="utf-8") as file:
        file.write(svg_content)

    print(f"SVG saved as: {output_svg_path}")

# Main function to handle command-line arguments
def main():
    parser = argparse.ArgumentParser(description="Color SVG file based on data from CSV.")
    parser.add_argument("csv_file", help="Path to the CSV file containing accident data.")
    parser.add_argument("title", help="Title to display on the SVG map.")
    args = parser.parse_args()

    process_files(args.csv_file, args.title)

if __name__ == "__main__":
    main()
