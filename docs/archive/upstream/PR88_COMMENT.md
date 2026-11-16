Tested this branch on another 64×16 panel reporting device type 131 (`0x83`). Using acknowledged GATT writes, a static pattern drawn with `set_pixels` rendered correctly: coloured corner markers, white dots and explicit black background clearing.

Thanks for adding this—grouping coordinates by colour fits our sparse Snake updates well, reducing a typical move from twelve individual pixel commands to three grouped commands.
