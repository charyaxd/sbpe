// macOS (x86_64, libc++) variant of internals.h
// The mac client is built with clang/libc++, so STL containers have
// different layouts than the 32-bit mingw/libstdc++ builds.
typedef unsigned char bool;

// ---------------------------------------------------------------------------
// C++ structs (as observed)

// std::string (libc++, default ABI, little endian), 24 bytes
//   short: byte0 = size << 1 (low bit 0), chars at +1 (max 22 + \0)
//   long:  cap | 1 at +0, size at +8, char* data at +16
struct STDString {
  union {
    struct {
      size_t cap;
      size_t size;
      char *data;
    } l;
    struct {
      unsigned char size;
      char data[23];
    } s_;
  };
};

// std::vector
struct STDVector { // length = v.finish - v.start / sizeof(elem_type)
  void *start; // points at the first element
  void *finish; // points _after_ the last element
  void *endOfStorage; // _after_ end of storage
};

// std::__hash_table (libc++)
struct STDHashtable {
  void *buckets;
  size_t bucket_count;
  void *first_node;
  size_t element_count;
  float max_load_factor;
};

// std::unordered_map
struct STDUMap {
  struct STDHashtable t;
};

// std::unordered_set
struct STDUSet {
  struct STDHashtable t;
};

// std::deque (libc++): __split_buffer<pointer> map + start + size
struct STDDeque {
  void *map_first;
  void *map_begin;
  void *map_end;
  void *map_end_cap;
  size_t start;
  size_t size;
};

// std::function (libc++ __value_func): 3-pointer inline buffer + __base*
struct STDFunction {
  void *buf[3];
  void *f;
};

// std::pair<uint, void*>
struct SortedVecElement {
  unsigned int key;
  void *obj;
};

// std::pair<Label*, Label*>
struct LabelPair {
  struct Label *first;
  struct Label *second;
};

// ---------------------------------------------------------------------------
// protobuf-related (2.x)

struct RepeatedPtrField {
  void **elements;
  int current_size;
  int allocated_size;
  int total_size;
};

struct RepeatedField_int {
  int32_t *elements;
  int current_size;
  int total_size;
};
