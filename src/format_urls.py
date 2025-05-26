# Read URLs from a file and format them for a Python list
input_file = 'urls.txt'
output_file = 'formatted12345678_urls.py'

# Read URLs from the input file
with open(input_file, 'r') as file:
    urls = file.readlines()

# Remove any trailing whitespace characters
urls = [url.strip() for url in urls]

# Create the formatted list of URLs
formatted_urls = ',\n'.join([f"'{url}'" for url in urls])

# Write the formatted URLs to the output file
with open(output_file, 'w') as file:
    file.write("video_urls = [\n")
    file.write(f"{formatted_urls}\n")
    file.write("]\n")

print(f"Formatted URLs have been saved to {output_file}")
