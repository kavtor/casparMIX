#include <cassert>
#include <core/frame/page_geometry.h>
#include <iostream>
#include <limits>
int main()
{
    auto quad = caspar::core::frame_geometry::get_default().data();
    using caspar::core::page_surface;
    for (int mode : {1, 2})
        for (bool reverse : {false, true})
            for (double radius : {.03, .16, .4})
                for (int n = 0; n <= 100; n++) {
                    page_surface s;
                    s.mode     = mode;
                    s.reverse  = reverse;
                    s.radius   = radius;
                    s.progress = n / 100.;
                    auto faces = caspar::core::page_mesh(quad, s);
                    assert(!faces.empty());
                    double depth = -1;
                    for (auto& face : faces) {
                        assert(face.depth >= depth - 1e-12);
                        depth = face.depth;
                        assert(face.coords.size() == 4);
                        for (auto& c : face.coords) {
                            assert(std::isfinite(c.vertex_x) && std::isfinite(c.vertex_y) &&
                                   std::isfinite(c.texture_r));
                            assert(c.texture_x >= 0 && c.texture_x <= 1 && c.texture_y >= 0 && c.texture_y <= 1);
                            assert(std::abs(c.texture_r) >= .59 && std::abs(c.texture_r) <= 1.01);
                            if (n == 0) {
                                assert(std::abs(c.vertex_x - c.texture_x) < 1e-10);
                                assert(std::abs(c.vertex_y - c.texture_y) < 1e-10);
                            }
                        }
                    }
                }
    std::cout
        << "PAGE GEOMETRY PASS: finite meshes, reversible UVs, depth ordering, endpoints and curvature extremes\n";
}
