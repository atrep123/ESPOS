#include "ui_font_6x8.h"

/* Helper: convert a 5-bit row pattern into a 6-bit mask with 1px spacing on the right. */
#define ROW5(bits5) ((uint8_t)((uint8_t)(bits5) << 1))

static const uint8_t GLYPH_SPACE[8] = { 0 };

static const uint8_t GLYPH_DOT[8] = {
    0x00, 0x00, 0x00, 0x00, 0x00, ROW5(0x04), ROW5(0x04), 0x00
};

static const uint8_t GLYPH_COLON[8] = {
    0x00, ROW5(0x04), ROW5(0x04), 0x00, ROW5(0x04), ROW5(0x04), 0x00, 0x00
};

static const uint8_t GLYPH_MINUS[8] = {
    0x00, 0x00, 0x00, ROW5(0x1F), 0x00, 0x00, 0x00, 0x00
};

static const uint8_t GLYPH_UNDERSCORE[8] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, ROW5(0x1F), 0x00
};

static const uint8_t GLYPH_SLASH[8] = {
    ROW5(0x01), ROW5(0x02), ROW5(0x04), ROW5(0x08), ROW5(0x10), 0x00, 0x00, 0x00
};

static const uint8_t GLYPH_QMARK[8] = {
    ROW5(0x0E), ROW5(0x11), ROW5(0x01), ROW5(0x02), ROW5(0x04), 0x00, ROW5(0x04), 0x00
};

static const uint8_t GLYPH_PERCENT[8] = {
    ROW5(0x19), ROW5(0x1A), ROW5(0x04), ROW5(0x08), ROW5(0x16), ROW5(0x06), 0x00, 0x00
};

/* Digits */
static const uint8_t GLYPH_0[8] = {
    ROW5(0x0E), ROW5(0x11), ROW5(0x11), ROW5(0x11), ROW5(0x11), ROW5(0x11), ROW5(0x0E), 0x00
};
static const uint8_t GLYPH_1[8] = {
    ROW5(0x04), ROW5(0x0C), ROW5(0x04), ROW5(0x04), ROW5(0x04), ROW5(0x04), ROW5(0x0E), 0x00
};
static const uint8_t GLYPH_2[8] = {
    ROW5(0x0E), ROW5(0x11), ROW5(0x01), ROW5(0x02), ROW5(0x04), ROW5(0x08), ROW5(0x1F), 0x00
};
static const uint8_t GLYPH_3[8] = {
    ROW5(0x0E), ROW5(0x11), ROW5(0x01), ROW5(0x06), ROW5(0x01), ROW5(0x11), ROW5(0x0E), 0x00
};
static const uint8_t GLYPH_4[8] = {
    ROW5(0x02), ROW5(0x06), ROW5(0x0A), ROW5(0x12), ROW5(0x1F), ROW5(0x02), ROW5(0x02), 0x00
};
static const uint8_t GLYPH_5[8] = {
    ROW5(0x1F), ROW5(0x10), ROW5(0x1E), ROW5(0x01), ROW5(0x01), ROW5(0x11), ROW5(0x0E), 0x00
};
static const uint8_t GLYPH_6[8] = {
    ROW5(0x06), ROW5(0x08), ROW5(0x10), ROW5(0x1E), ROW5(0x11), ROW5(0x11), ROW5(0x0E), 0x00
};
static const uint8_t GLYPH_7[8] = {
    ROW5(0x1F), ROW5(0x01), ROW5(0x02), ROW5(0x04), ROW5(0x08), ROW5(0x08), ROW5(0x08), 0x00
};
static const uint8_t GLYPH_8[8] = {
    ROW5(0x0E), ROW5(0x11), ROW5(0x11), ROW5(0x0E), ROW5(0x11), ROW5(0x11), ROW5(0x0E), 0x00
};
static const uint8_t GLYPH_9[8] = {
    ROW5(0x0E), ROW5(0x11), ROW5(0x11), ROW5(0x0F), ROW5(0x01), ROW5(0x02), ROW5(0x0C), 0x00
};

/* Uppercase letters */
static const uint8_t GLYPH_A[8] = {
    ROW5(0x0E), ROW5(0x11), ROW5(0x11), ROW5(0x1F), ROW5(0x11), ROW5(0x11), ROW5(0x11), 0x00
};
static const uint8_t GLYPH_B[8] = {
    ROW5(0x1E), ROW5(0x11), ROW5(0x11), ROW5(0x1E), ROW5(0x11), ROW5(0x11), ROW5(0x1E), 0x00
};
static const uint8_t GLYPH_C[8] = {
    ROW5(0x0E), ROW5(0x11), ROW5(0x10), ROW5(0x10), ROW5(0x10), ROW5(0x11), ROW5(0x0E), 0x00
};
static const uint8_t GLYPH_D[8] = {
    ROW5(0x1E), ROW5(0x11), ROW5(0x11), ROW5(0x11), ROW5(0x11), ROW5(0x11), ROW5(0x1E), 0x00
};
static const uint8_t GLYPH_E[8] = {
    ROW5(0x1F), ROW5(0x10), ROW5(0x10), ROW5(0x1E), ROW5(0x10), ROW5(0x10), ROW5(0x1F), 0x00
};
static const uint8_t GLYPH_F[8] = {
    ROW5(0x1F), ROW5(0x10), ROW5(0x10), ROW5(0x1E), ROW5(0x10), ROW5(0x10), ROW5(0x10), 0x00
};
static const uint8_t GLYPH_G[8] = {
    ROW5(0x0E), ROW5(0x11), ROW5(0x10), ROW5(0x17), ROW5(0x11), ROW5(0x11), ROW5(0x0E), 0x00
};
static const uint8_t GLYPH_H[8] = {
    ROW5(0x11), ROW5(0x11), ROW5(0x11), ROW5(0x1F), ROW5(0x11), ROW5(0x11), ROW5(0x11), 0x00
};
static const uint8_t GLYPH_I[8] = {
    ROW5(0x0E), ROW5(0x04), ROW5(0x04), ROW5(0x04), ROW5(0x04), ROW5(0x04), ROW5(0x0E), 0x00
};
static const uint8_t GLYPH_J[8] = {
    ROW5(0x01), ROW5(0x01), ROW5(0x01), ROW5(0x01), ROW5(0x11), ROW5(0x11), ROW5(0x0E), 0x00
};
static const uint8_t GLYPH_K[8] = {
    ROW5(0x11), ROW5(0x12), ROW5(0x14), ROW5(0x18), ROW5(0x14), ROW5(0x12), ROW5(0x11), 0x00
};
static const uint8_t GLYPH_L[8] = {
    ROW5(0x10), ROW5(0x10), ROW5(0x10), ROW5(0x10), ROW5(0x10), ROW5(0x10), ROW5(0x1F), 0x00
};
static const uint8_t GLYPH_M[8] = {
    ROW5(0x11), ROW5(0x1B), ROW5(0x15), ROW5(0x15), ROW5(0x11), ROW5(0x11), ROW5(0x11), 0x00
};
static const uint8_t GLYPH_N[8] = {
    ROW5(0x11), ROW5(0x19), ROW5(0x15), ROW5(0x13), ROW5(0x11), ROW5(0x11), ROW5(0x11), 0x00
};
static const uint8_t GLYPH_O[8] = {
    ROW5(0x0E), ROW5(0x11), ROW5(0x11), ROW5(0x11), ROW5(0x11), ROW5(0x11), ROW5(0x0E), 0x00
};
static const uint8_t GLYPH_P[8] = {
    ROW5(0x1E), ROW5(0x11), ROW5(0x11), ROW5(0x1E), ROW5(0x10), ROW5(0x10), ROW5(0x10), 0x00
};
static const uint8_t GLYPH_Q[8] = {
    ROW5(0x0E), ROW5(0x11), ROW5(0x11), ROW5(0x11), ROW5(0x15), ROW5(0x12), ROW5(0x0D), 0x00
};
static const uint8_t GLYPH_R[8] = {
    ROW5(0x1E), ROW5(0x11), ROW5(0x11), ROW5(0x1E), ROW5(0x14), ROW5(0x12), ROW5(0x11), 0x00
};
static const uint8_t GLYPH_S[8] = {
    ROW5(0x0F), ROW5(0x10), ROW5(0x10), ROW5(0x0E), ROW5(0x01), ROW5(0x01), ROW5(0x1E), 0x00
};
static const uint8_t GLYPH_T[8] = {
    ROW5(0x1F), ROW5(0x04), ROW5(0x04), ROW5(0x04), ROW5(0x04), ROW5(0x04), ROW5(0x04), 0x00
};
static const uint8_t GLYPH_U[8] = {
    ROW5(0x11), ROW5(0x11), ROW5(0x11), ROW5(0x11), ROW5(0x11), ROW5(0x11), ROW5(0x0E), 0x00
};
static const uint8_t GLYPH_V[8] = {
    ROW5(0x11), ROW5(0x11), ROW5(0x11), ROW5(0x11), ROW5(0x0A), ROW5(0x0A), ROW5(0x04), 0x00
};
static const uint8_t GLYPH_W[8] = {
    ROW5(0x11), ROW5(0x11), ROW5(0x11), ROW5(0x15), ROW5(0x15), ROW5(0x1B), ROW5(0x11), 0x00
};
static const uint8_t GLYPH_X[8] = {
    ROW5(0x11), ROW5(0x0A), ROW5(0x0A), ROW5(0x04), ROW5(0x0A), ROW5(0x0A), ROW5(0x11), 0x00
};
static const uint8_t GLYPH_Y[8] = {
    ROW5(0x11), ROW5(0x0A), ROW5(0x04), ROW5(0x04), ROW5(0x04), ROW5(0x04), ROW5(0x04), 0x00
};
static const uint8_t GLYPH_Z[8] = {
    ROW5(0x1F), ROW5(0x01), ROW5(0x02), ROW5(0x04), ROW5(0x08), ROW5(0x10), ROW5(0x1F), 0x00
};
static const uint8_t GLYPH_PLUS[8] = {
    0x00, ROW5(0x04), ROW5(0x04), ROW5(0x1F), ROW5(0x04), ROW5(0x04), 0x00, 0x00
};
static const uint8_t GLYPH_LT[8] = {
    ROW5(0x02), ROW5(0x04), ROW5(0x08), ROW5(0x10), ROW5(0x08), ROW5(0x04), ROW5(0x02), 0x00
};
static const uint8_t GLYPH_GT[8] = {
    ROW5(0x08), ROW5(0x04), ROW5(0x02), ROW5(0x01), ROW5(0x02), ROW5(0x04), ROW5(0x08), 0x00
};
static const uint8_t GLYPH_EXCL[8] = {
    ROW5(0x04), ROW5(0x04), ROW5(0x04), ROW5(0x04), ROW5(0x04), 0x00, ROW5(0x04), 0x00
};
static const uint8_t GLYPH_EQ[8] = {
    0x00, 0x00, ROW5(0x1F), 0x00, ROW5(0x1F), 0x00, 0x00, 0x00
};
static const uint8_t GLYPH_LPAREN[8] = {
    ROW5(0x02), ROW5(0x04), ROW5(0x08), ROW5(0x08), ROW5(0x08), ROW5(0x04), ROW5(0x02), 0x00
};
static const uint8_t GLYPH_RPAREN[8] = {
    ROW5(0x08), ROW5(0x04), ROW5(0x02), ROW5(0x02), ROW5(0x02), ROW5(0x04), ROW5(0x08), 0x00
};
static const uint8_t GLYPH_COMMA[8] = {
    0x00, 0x00, 0x00, 0x00, 0x00, ROW5(0x04), ROW5(0x04), ROW5(0x08)
};
static const uint8_t GLYPH_HASH[8] = {
    ROW5(0x0A), ROW5(0x0A), ROW5(0x1F), ROW5(0x0A), ROW5(0x1F), ROW5(0x0A), ROW5(0x0A), 0x00
};
static const uint8_t GLYPH_STAR[8] = {
    0x00, ROW5(0x04), ROW5(0x15), ROW5(0x0E), ROW5(0x15), ROW5(0x04), 0x00, 0x00
};

const uint8_t *ui_font6x8_glyph(char c)
{
    if (c >= 'a' && c <= 'z') {
        c = (char)(c - 'a' + 'A');
    }

    switch (c) {
        case ' ':
            return GLYPH_SPACE;
        case '.':
            return GLYPH_DOT;
        case ':':
            return GLYPH_COLON;
        case '-':
            return GLYPH_MINUS;
        case '_':
            return GLYPH_UNDERSCORE;
        case '/':
            return GLYPH_SLASH;
        case '%':
            return GLYPH_PERCENT;
        case '?':
            return GLYPH_QMARK;
        case '+':
            return GLYPH_PLUS;
        case '<':
            return GLYPH_LT;
        case '>':
            return GLYPH_GT;
        case '!':
            return GLYPH_EXCL;
        case '=':
            return GLYPH_EQ;
        case '(':
            return GLYPH_LPAREN;
        case ')':
            return GLYPH_RPAREN;
        case ',':
            return GLYPH_COMMA;
        case '#':
            return GLYPH_HASH;
        case '*':
            return GLYPH_STAR;

        case '0':
            return GLYPH_0;
        case '1':
            return GLYPH_1;
        case '2':
            return GLYPH_2;
        case '3':
            return GLYPH_3;
        case '4':
            return GLYPH_4;
        case '5':
            return GLYPH_5;
        case '6':
            return GLYPH_6;
        case '7':
            return GLYPH_7;
        case '8':
            return GLYPH_8;
        case '9':
            return GLYPH_9;

        case 'A':
            return GLYPH_A;
        case 'B':
            return GLYPH_B;
        case 'C':
            return GLYPH_C;
        case 'D':
            return GLYPH_D;
        case 'E':
            return GLYPH_E;
        case 'F':
            return GLYPH_F;
        case 'G':
            return GLYPH_G;
        case 'H':
            return GLYPH_H;
        case 'I':
            return GLYPH_I;
        case 'J':
            return GLYPH_J;
        case 'K':
            return GLYPH_K;
        case 'L':
            return GLYPH_L;
        case 'M':
            return GLYPH_M;
        case 'N':
            return GLYPH_N;
        case 'O':
            return GLYPH_O;
        case 'P':
            return GLYPH_P;
        case 'Q':
            return GLYPH_Q;
        case 'R':
            return GLYPH_R;
        case 'S':
            return GLYPH_S;
        case 'T':
            return GLYPH_T;
        case 'U':
            return GLYPH_U;
        case 'V':
            return GLYPH_V;
        case 'W':
            return GLYPH_W;
        case 'X':
            return GLYPH_X;
        case 'Y':
            return GLYPH_Y;
        case 'Z':
            return GLYPH_Z;

        default:
            return GLYPH_QMARK;
    }
}

