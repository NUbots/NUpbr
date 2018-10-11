#include <iostream>
#include <limits>
#include <string>
#include <vector>

#include <OpenEXR/ImathBox.h>
#include <OpenEXR/ImfArray.h>
#include <OpenEXR/ImfChannelList.h>
#include <OpenEXR/ImfFrameBuffer.h>
#include <OpenEXR/ImfInputFile.h>
#include <OpenEXR/ImfOutputFile.h>
#include <OpenEXR/ImfPixelType.h>

namespace openexr = OPENEXR_IMF_INTERNAL_NAMESPACE;

struct DepthImage {
    DepthImage(const std::string& file_name) : file_name(file_name), depth(), width(0), height(0) {}

    std::string file_name;
    openexr::Array2D<float> depth;
    int width;
    int height;
};

void readDepthImage(DepthImage& image);
void writeDisparity(const DepthImage& image, const std::string& output_file, float focal_length, float baseline);

int main(int argc, char** argv) {
    DepthImage image(argv[1]);
    std::string output_file(argv[2]);
    float focal_length(std::stof(argv[3]));
    float baseline(std::stof(argv[4]));

    readDepthImage(image);
    writeDisparity(image, output_file, focal_length, baseline);

    return 0;
}

void readDepthImage(DepthImage& image) {
    openexr::InputFile input_file(image.file_name.c_str());
    IMATH_INTERNAL_NAMESPACE::Box2i dw = input_file.header().dataWindow();
    image.width                        = dw.max.x - dw.min.x + 1;
    image.height                       = dw.max.y - dw.min.y + 1;
    image.depth.resizeErase(image.height, image.width);

    openexr::FrameBuffer frameBuffer;
    frameBuffer.insert(
        "R",                                                                                             // name
        openexr::Slice(openexr::FLOAT,                                                                   // type
                       reinterpret_cast<char*>(&image.depth[0][0] - dw.min.x - dw.min.y * image.width),  // base
                       sizeof(image.depth[0][0]) * 1,                                                    // xStride
                       sizeof(image.depth[0][0]) * image.width,                                          // yStride
                       1,                                                                                // x sampling
                       1,                                                                                // y sampling
                       std::numeric_limits<float>::infinity()));                                         // fillValue

    input_file.setFrameBuffer(frameBuffer);
    input_file.readPixels(dw.min.y, dw.max.y);
}

void writeDisparity(const DepthImage& image, const std::string& output_file, float focal_length, float baseline) {
    openexr::Header header(image.width, image.height);
    header.channels().insert("D", openexr::Channel(openexr::FLOAT));

    openexr::OutputFile disparity_file(output_file.c_str(), header);

    const float fB = focal_length * baseline;
    std::vector<float> disparity(image.depth[0], image.depth[0] + image.depth.width() * image.depth.height());
    for (int i = 0; i < image.depth.width() * image.depth.height(); i++) {
        disparity[i] = fB / disparity[i];
    }

    openexr::FrameBuffer frameBuffer;
    frameBuffer.insert("D",                                                       // name
                       openexr::Slice(openexr::FLOAT,                             // type
                                      reinterpret_cast<char*>(disparity.data()),  // base
                                      sizeof(*disparity.data()) * 1,              // xStride
                                      sizeof(*disparity.data()) * image.width));  // yStride

    disparity_file.setFrameBuffer(frameBuffer);
    disparity_file.writePixels(image.height);
}
