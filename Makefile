INC_DIR=include
SRC_DIR=src
OBJ_DIR=obj
BIN_DIR=bin

INCLUDE_DIRS =  -I$(INC_DIR) -I/usr/include/opencv4

LIB_DIRS = 
CPPC=g++

#------------------------------------------------------------------------------
# cuda specific code
CUDA_PATH= /usr/local/cuda
CUDA_INC_PATH= $(CUDA_PATH)/include
CUDA_BIN_PATH= $(CUDA_PATH)/bin
CUDA_LIB_PATH= $(CUDA_PATH)/lib64

NVCC=$(CUDA_BIN_PATH)/nvcc
NVCC_FLAGS=--std=c++17 -O3 $(INCLUDE_DIRS)
#------------------------------------------------------------------------------

EXE=$(BIN_DIR)/main

# OpenCV and CUDA stuff
#CPP_DEFS=
#CPP_FLAGS=--std=c++17 -O3 $(INCLUDE_DIRS) $(CPP_DEFS)
#LIBS=-lpthread -L/usr/lib -L$(CUDA_LIB_PATH) -lcuda -lcudart -lopencv_core -lopencv_flann -lopencv_video -lrt

CPP_DEFS=
CPP_FLAGS=--std=c++17 -Wall -Werror $(INCLUDE_DIRS) $(CPP_DEFS)
LIBS=-lpthread -L/usr/lib -lopencv_core -lopencv_flann -lopencv_video -lrt

CPP_SRCS=$(wildcard $(SRC_DIR)/*.cpp)
CPP_OBJS=$(CPP_SRCS:$(SRC_DIR)/%.cpp=$(OBJ_DIR)/%.o)

#CUDA_SRCS=$(wildcard $(SRC_DIR)/*.cu)
#CUDA_OBJS=$(CUDA_SRCS:$(SRC_DIR)/%.cu=$(OBJ_DIR)/%.o)

.PHONY: all clean

all: $(EXE) $(USB_EXE)

# the BIN_DIR at the end will mark the target as requiring it but is not the
# same as the file requirements
$(EXE): $(CPP_OBJS) $(CUDA_OBJS) | $(BIN_DIR)
	$(CPPC) $(CPP_FLAGS) -o $@ $^ `pkg-config --libs opencv4` $(LIBS)

# place back in the above target when opencv is on the system
#$(CPPC) $(CPP_FLAGS) -o $@ $^ `pkg-config --libs opencv4` $(LIBS)

# pattern rule, will specify targets .o targets for cpp files and then build
# them with the cpp compiler
$(OBJ_DIR)/%.o: $(SRC_DIR)/%.cpp | $(OBJ_DIR)
	$(CPPC) $(CPP_FLAGS) -c $< -o $@

# similar rule as the cpp files but for the CUDA files in the src directory
#$(OBJ_DIR)/%.o: $(SRC_DIR)/%.cu | $(OBJ_DIR)
#	$(NVCC) $(NVCC_FLAGS) -c $< -o $@

# rules for the build and obj directory that will create them if they do not
# exist
$(BIN_DIR) $(OBJ_DIR):
	mkdir -p $@

clean:
	-rm -Rd $(BIN_DIR) $(OBJ_DIR)
