// stl-splitter: possible source of for slicing an stl model. will require
// a deeper dive as I currently do not know if there is a repsitory available
// to reference. the code is available on the site and is not minified or
// obscured so it can be referenced.
//
// site source: https://www.stl-splitter.com/
// 
// the original python code found that looked like it could work has having
#include <exception>
#include <iostream>
#include <utility>

#include <CLI11.hpp>
#include <stl_reader.hpp>

struct MinMax {
    float min = -INFINITY;
    float max = INFINITY;
}

struct StlBounds {
    MinMax x;
    MinMax y;
    MinMax z;
}

StlBounds compute_bounds(
    const std::vector<float> triangles,
    const std::vector<unsigned int> coords,
);

int main(int argc, char** argv) {
    CLI::App app{"geo-spector"};
    argv = app.ensure_utf8(argv);

    std::string input_stl = "";

    app.add_option("-s,--stl", input_stl, "the input stl file to load");

    CLI11_PARSE(app, argc, argv);

    if (input_stl.empty()) {
        std::cout << "no stl file specified\n";

        return 1;
    }

    // example 3 from stl_reader repo
    // the list of coordinates for the entire model
    std::vector<float> coords;
    // the list of normals for each triangle in the model
    std::vector<float> normals;
    // the list of index's used to access coords that are used to create a
    // triangle
    std::vector<unsigned int> tris;
    std::vector<unsigned int> solids;

    try {
        stl_reader::ReadStlFile(input_stl.c_str(), coords, normals, tris, solids);
    } catch (std::exception& err) {
        std::cout << "failed to load stl file: " << err.what() << "\n";

        return 1;
    }

    const std::size_t num_tris = tris.size() / 3;

    std::cout << "triangles: " << tris.size() << " " << num_tris << "\n";

    for (std::size_t index_tri = 0; index_tri < num_tris; index_tri += 1) {
        std::size_t offset = 3 * index_tri;
        std::cout << "triangle: (" << tris[offset] << ", " << tris[offset + 1] << ", " << tris[offset + 2] << ")\n";
    }

    const std::size_t num_normals = normals.size() / 3;

    std::cout << "normals: " << normals.size() << " " << num_normals << "\n";

    for (std::size_t index_normals = 0; index_normals < num_normals; index_normals += 1) {
        std::size_t offset = 3 * index_normals;
        std::cout << "normal: (" << normals[offset] << ", " << normals[offset + 1] << ", " << normals[offset + 2] << ")\n";
    }

    const std::size_t num_coords = coords.size() / 3;

    std::cout << "coords: " << coords.size() << " " << num_coords << "\n";

    for (std::size_t index_coords = 0; index_coords < num_coords; index_coords += 1) {
        std::size_t offset = 3 * index_coords;
        std::cout << "coord: (" << coords[offset] << ", " << coords[offset + 1] << ", " << coords[offset + 2] << ")\n";
    }

    std::cout << "solids: " << solids.size() << "\n";

    for (std::size_t index_solids = 0; index_solids < solids.size(); index_solids += 1) {
        std::cout << solids[index_solids] << "\n";
    }

    std::cout << "coordinates of triangles:\n";

    // this is the code from the example to illustrate accessing data for a triangle
    for (std::size_t index_tri = 0; index_tri < num_tris; index_tri += 1) {
        std::cout << "coordinates of triangle " << index_tri << ": ";

        for (std::size_t index_corner = 0; index_corner < 3; index_corner += 1) {
            float* c = &coords[3 * tris[3 * index_tri + index_corner]];

            std::cout << "(" << c[0] << ", " << c[1] << ", " << c[2] << ") ";
        }

        std::cout << "\n";
    }

    return 0;
}

StlBounds compute_bounds(
    const std::vector<float> triangles,
    const std::vector<unsigned int> coords,
) {
    StlBounds rtn;

    
}
