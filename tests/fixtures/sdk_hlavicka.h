// Mala fixtura pro `validate_design.jmena_ze_sdk`.
//
// NENI to kopie SDK TabOSu - je to nosic obou tvaru, ktere ta funkce cte,
// plus tvary, ktere cist NEMA. Kopie ziveho SDK by test promenila v druhy
// opis seznamu jmen, a prave opsany seznam je to, cemu se pravidlo 142
// vyhyba.
#pragma once

namespace test_sdk {

// (1) jmeno rozhrani podle konvence repa: velke I + CamelCase
class IHwDiagnostics {
public:
    virtual ~IHwDiagnostics() = default;
};

struct IRadioInfo {
    int rssi;
};

// (2) hodnoty enumu, vcetne tvaru s prirazenim a s typem za dvojteckou
enum class Error : unsigned short {
    None = 0,
    InvalidArgument,
    Unavailable,
    NotFound
};

enum class DataState : unsigned char { Live, Cached, Mock };

// Co se cist NEMA:
class DesktopMock {};        // neni rozhrani (nezacina I + velkym pismenem)
struct Ihned {};             // I + male pismeno = ceske slovo, ne konvence
class I2cSbernice {};        // taky male pismeno hned za I
void unavailableSomewhere(); // funkce, ne hodnota enumu

}  // namespace test_sdk
