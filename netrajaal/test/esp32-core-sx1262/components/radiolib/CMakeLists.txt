# RadioLib Component for ESP-IDF
# This component wraps RadioLib library for use with ESP-IDF

idf_component_register(
    SRCS ""
    INCLUDE_DIRS "."
    REQUIRES ""
)

# Add RadioLib as an external component
# Note: You need to clone RadioLib into this directory or use a git submodule
# git clone https://github.com/jgromes/RadioLib.git .

# For now, we'll assume RadioLib is available via Arduino framework
# or installed as a component in your project

