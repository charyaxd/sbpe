#include "MaxRectsBinPack.h"
#include <vector>

using namespace rbp;

MaxRectsBinPack mbp;

std::vector<Rect> dst;

// a real enum (MSVC accepted the previous forward-referenced enum + ints,
// clang/gcc do not); values mirror the library's own heuristic enum
enum MaxRectsFreeRectChoiceHeuristic {
	MaxRectsBestShortSideFit = MaxRectsBinPack::RectBestShortSideFit, ///< -BSSF
	MaxRectsBestLongSideFit = MaxRectsBinPack::RectBestLongSideFit, ///< -BLSF
	MaxRectsBestAreaFit = MaxRectsBinPack::RectBestAreaFit, ///< -BAF
	MaxRectsBottomLeftRule = MaxRectsBinPack::RectBottomLeftRule, ///< -BL
	MaxRectsContactPointRule = MaxRectsBinPack::RectContactPointRule ///< -CP
};


extern "C" {

void MaxRects_init(int width, int height, bool flip) {
    mbp.Init(width, height, flip);
}

struct Rect MaxRects_insertOne(int width, int height, enum MaxRectsFreeRectChoiceHeuristic method) {
	return mbp.Insert(width, height, (MaxRectsBinPack::FreeRectChoiceHeuristic)method);
}

unsigned int MaxRects_insert(struct RectSize *sizes, int num, enum MaxRectsFreeRectChoiceHeuristic method, struct Rect **out) {
	std::vector<RectSize> rects(sizes, sizes + num);
	mbp.Insert(rects, dst, (MaxRectsBinPack::FreeRectChoiceHeuristic)method);
	*out = dst.data();
	return dst.size();
}

float MaxRects_occupancy() {
	return mbp.Occupancy();
}

}
