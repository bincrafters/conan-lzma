#include <lzma.h>
#include <iostream>

int main()
{
    std::cout << "LZMA version " << lzma_version_string() << std::endl;
}
