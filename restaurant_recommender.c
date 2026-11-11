#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
#include <windows.h>
#define POPEN _popen
#define PCLOSE _pclose
#define STDERR_NULL "NUL"
#else
#define POPEN popen
#define PCLOSE pclose
#define STDERR_NULL "/dev/null"
#endif

#define MAX_FIELD 512
#define MAX_FIELDS 24
#define SHOW_STEP 5

/*
    혜화 식당 추천 시스템 - terminal 중심 개선 버전
    핵심 자료구조: Linked List

    - 기본 위치는 혜화역입니다.
    - 추천 결과는 터미널에서 관리합니다.
    - 영업 중인 식당만 추천 목록에 넣습니다.
    - 삭제는 영구 제외, 보류는 나중에 복구 가능합니다.
*/

typedef struct
{
    char want_genre[32];
    char mood[32];
    int left_time;
    int headcount;
    int hungriness;
    int poor;
    char before_eat[32];
    char next_route[64];
} User;

typedef struct
{
    char id[32];
    char name[128];
    char genre[32];
    char location[256];
    int open_time;
    int close_time;
    float rating;
    int price;
    int speed;
    int break_start;
    int break_end;
    float distance;
    char kakao_url[256];
    float lat;
    float lon;
    int has_location;
    int available;
    int score;
} Rest;

typedef struct Node
{
    Rest rest;
    struct Node* next;
} Node;

void user_init(User* user);
int open_main_ui(void);
int ask_mode_terminal(void);
void get_user_information(User* user);
void read_user_settings(User* user);
void prepare_location_and_distance(void);
void cal_time(int* now_time);
void print_current_time(int now_time);
int cal_availability(Rest* rest, int now_time);
int cal_consistency(User* user, Rest* rest, int mode);
void make_list(Node* head, User* user, int now_time, int mode);
void insert_node_sorted(Node* head, Node* node);
Node* pop_node(Node* head, int index);
Node* get_node(Node* head, int index);
void append_node(Node* head, Node* node);
void free_list(Node* head);
void show_recommend_list(Node* recommend_head, int show_count);
void show_sub_list(Node* head, char* title);
void save_list_to_file(Node* head, char* filename);
void save_top_n_to_file(Node* head, char* filename, int n);
void save_one_to_file(Node* node, char* filename);
void print_command_help(void);
int run_terminal(Node* recommend_head);
void init_console(void);
int run_python_script(const char* script, const char* arg1, const char* arg2);
int read_python_stdout_int(const char* script);

static void strip_newline(char* s)
{
    int len = (int)strlen(s);
    while (len > 0 && (s[len - 1] == '\n' || s[len - 1] == '\r'))
    {
        s[len - 1] = '\0';
        len--;
    }
}

static int is_empty_text(char* s)
{
    if (s == NULL)
        return 1;
    if (s[0] == '\0')
        return 1;
    if (strcmp(s, "None") == 0 || strcmp(s, "none") == 0 || strcmp(s, "NULL") == 0)
        return 1;
    return 0;
}

static int to_int_default(char* s, int default_value)
{
    if (is_empty_text(s))
        return default_value;
    return atoi(s);
}

static float to_float_default(char* s, float default_value)
{
    if (is_empty_text(s))
        return default_value;
    return (float)atof(s);
}

static void safe_copy(char* dest, const char* src, int size)
{
    if (size <= 0)
        return;

    if (src == NULL)
        src = "";

    strncpy(dest, src, size - 1);
    dest[size - 1] = '\0';
}

static int contains_text(const char* text, const char* key)
{
    if (text == NULL || key == NULL)
        return 0;
    return strstr(text, key) != NULL;
}

static int is_valid_mood(const char* mood)
{
    if (mood == NULL)
        return 0;

    return strcmp(mood, "없음") == 0 ||
           strcmp(mood, "데이트") == 0 ||
           strcmp(mood, "혼밥") == 0 ||
           strcmp(mood, "술") == 0;
}

static void normalize_mood(User* user)
{
    if (!is_valid_mood(user->mood))
        safe_copy(user->mood, "없음", sizeof(user->mood));
}

/* 간단 CSV parser입니다. 따옴표 안의 쉼표도 어느 정도 처리합니다. */
static int split_csv(char* line, char fields[][MAX_FIELD], int max_fields)
{
    int count = 0;
    int i = 0;
    int j = 0;
    int in_quote = 0;

    for (count = 0; count < max_fields; count++)
        fields[count][0] = '\0';

    count = 0;

    while (line[i] != '\0' && count < max_fields)
    {
        char c = line[i];

        if (c == '"')
        {
            if (in_quote && line[i + 1] == '"')
            {
                if (j < MAX_FIELD - 1)
                    fields[count][j++] = '"';
                i++;
            }
            else
                in_quote = !in_quote;
        }
        else if (c == ',' && !in_quote)
        {
            fields[count][j] = '\0';
            count++;
            j = 0;
        }
        else if (c != '\n' && c != '\r')
        {
            if (j < MAX_FIELD - 1)
                fields[count][j++] = c;
        }
        i++;
    }

    if (count < max_fields)
    {
        fields[count][j] = '\0';
        count++;
    }

    return count;
}

static void write_csv_text(FILE* fp, const char* text)
{
    int need_quote = 0;
    int i;

    if (text == NULL)
        text = "";

    for (i = 0; text[i] != '\0'; i++)
    {
        if (text[i] == ',' || text[i] == '"' || text[i] == '\n' || text[i] == '\r')
        {
            need_quote = 1;
            break;
        }
    }

    if (!need_quote)
    {
        fprintf(fp, "%s", text);
        return;
    }

    fputc('"', fp);
    for (i = 0; text[i] != '\0'; i++)
    {
        if (text[i] == '"')
            fputc('"', fp);
        fputc(text[i], fp);
    }
    fputc('"', fp);
}


void init_console(void)
{
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleCP(CP_UTF8);
    system("chcp 65001 > NUL");
#endif
}

static int run_python_command(const char* python_cmd, const char* script, const char* arg1, const char* arg2)
{
    char command[768];

    if (arg1 != NULL && arg2 != NULL)
        snprintf(command, sizeof(command), "%s \"%s\" \"%s\" \"%s\"", python_cmd, script, arg1, arg2);
    else if (arg1 != NULL)
        snprintf(command, sizeof(command), "%s \"%s\" \"%s\"", python_cmd, script, arg1);
    else
        snprintf(command, sizeof(command), "%s \"%s\"", python_cmd, script);

    return system(command);
}

int run_python_script(const char* script, const char* arg1, const char* arg2)
{
    int result;

#ifdef _WIN32
    result = run_python_command("py -3", script, arg1, arg2);
    if (result != 0)
        result = run_python_command("python", script, arg1, arg2);
#else
    result = run_python_command("python3", script, arg1, arg2);
    if (result != 0)
        result = run_python_command("python", script, arg1, arg2);
#endif

    return result;
}

static int read_python_stdout_int_by_command(const char* python_cmd, const char* script)
{
    FILE* fp;
    char command[512];
    char result[32];
    int mode = -1;

    snprintf(command, sizeof(command), "%s \"%s\" 2>%s", python_cmd, script, STDERR_NULL);
    fp = POPEN(command, "r");

    if (fp == NULL)
        return -1;

    if (fgets(result, sizeof(result), fp) != NULL)
        mode = atoi(result);

    PCLOSE(fp);
    return mode;
}

int read_python_stdout_int(const char* script)
{
    int mode;

#ifdef _WIN32
    mode = read_python_stdout_int_by_command("py -3", script);
    if (mode < 0)
        mode = read_python_stdout_int_by_command("python", script);
#else
    mode = read_python_stdout_int_by_command("python3", script);
    if (mode < 0)
        mode = read_python_stdout_int_by_command("python", script);
#endif

    return mode;
}

void user_init(User* user)
{
    safe_copy(user->want_genre, "한식", sizeof(user->want_genre));
    safe_copy(user->mood, "없음", sizeof(user->mood));
    user->left_time = 60;
    user->headcount = 1;
    user->hungriness = 3;
    user->poor = 3;
    safe_copy(user->before_eat, "없음", sizeof(user->before_eat));
    safe_copy(user->next_route, "학교", sizeof(user->next_route));
}

int open_main_ui(void)
{
    return read_python_stdout_int("main_ui.py");
}

int ask_mode_terminal(void)
{
    int mode;

    printf("\nmain 화면을 열 수 없어서 터미널로 진행합니다....\n");
    printf("0. random\n");
    printf("1. favorites(settings)\n");
    printf("2. customize\n");
    printf("9. exit\n");
    printf("선택 >> ");

    if (scanf("%d", &mode) != 1)
        mode = 0;

    while (getchar() != '\n')
        ;

    if (!((mode >= 0 && mode <= 2) || mode == 9))
        mode = 0;

    return mode;
}

void get_user_information(User* user)
{
    printf("\n==== [사용자 정보 입력] ====\n");

    printf("1. 먹고 싶은 종류 >> ");
    scanf("%31s", user->want_genre);

    printf("2. 원하는 식당 분위기(없음/데이트/혼밥/술) >> ");
    scanf("%31s", user->mood);
    normalize_mood(user);

    printf("3. 남은 시간(분) >> ");
    scanf("%d", &user->left_time);

    printf("4. 인원 수 >> ");
    scanf("%d", &user->headcount);

    printf("5. 배고픔 정도(1-5) >> ");
    scanf("%d", &user->hungriness);

    printf("6. 가격 민감도(1-5) >> ");
    scanf("%d", &user->poor);

    printf("7. 최근 먹은 종류 >> ");
    scanf("%31s", user->before_eat);

    printf("8. 다음 목적지 >> ");
    scanf("%63s", user->next_route);

    while (getchar() != '\n')
        ;

    printf("============================\n");
}

void read_user_settings(User* user)
{
    FILE* fp = fopen("user_settings.txt", "r");
    char line[128];

    if (fp == NULL)
    {
        printf("저장된 settings가 없어서 기본값으로 진행합니다....\n");
        return;
    }

    if (fgets(line, sizeof(line), fp) != NULL)
    {
        strip_newline(line);
        safe_copy(user->want_genre, line, sizeof(user->want_genre));
    }
    if (fgets(line, sizeof(line), fp) != NULL)
    {
        strip_newline(line);
        safe_copy(user->mood, line, sizeof(user->mood));
        normalize_mood(user);
    }
    if (fgets(line, sizeof(line), fp) != NULL) user->left_time = atoi(line);
    if (fgets(line, sizeof(line), fp) != NULL) user->headcount = atoi(line);
    if (fgets(line, sizeof(line), fp) != NULL) user->hungriness = atoi(line);
    if (fgets(line, sizeof(line), fp) != NULL) user->poor = atoi(line);
    if (fgets(line, sizeof(line), fp) != NULL)
    {
        strip_newline(line);
        safe_copy(user->before_eat, line, sizeof(user->before_eat));
    }
    if (fgets(line, sizeof(line), fp) != NULL)
    {
        strip_newline(line);
        safe_copy(user->next_route, line, sizeof(user->next_route));
    }

    fclose(fp);
}

void prepare_location_and_distance(void)
{
    fflush(stdout);
    run_python_script("choose_location.py", NULL, NULL);

    printf("식당 정보를 준비합니다....\n");
    fflush(stdout);
    run_python_script("update_route_distances.py", NULL, NULL);
}

void cal_time(int* now_time)
{
    time_t current;
    struct tm* t;

    current = time(NULL);
    t = localtime(&current);

    *now_time = (t->tm_hour) * 100 + (t->tm_min);
}

void print_current_time(int now_time)
{
    int hour = now_time / 100;
    int minute = now_time % 100;
    int display_hour;
    char* ampm;

    if (hour < 12)
        ampm = "오전";
    else
        ampm = "오후";

    display_hour = hour % 12;
    if (display_hour == 0)
        display_hour = 12;

    printf("\n현재 시각 : %s %d시 %02d분\n", ampm, display_hour, minute);
}

static int is_time_between(int now_time, int start_time, int end_time)
{
    if (start_time == 0 && end_time == 0)
        return 0;

    if (start_time <= end_time)
        return now_time >= start_time && now_time <= end_time;

    return now_time >= start_time || now_time <= end_time;
}

int cal_availability(Rest* rest, int now_time)
{
    int open_ok;
    int break_now;

    open_ok = is_time_between(now_time, rest->open_time, rest->close_time);
    break_now = is_time_between(now_time, rest->break_start, rest->break_end);

    if (open_ok && !break_now)
        rest->available = 1;
    else
        rest->available = 0;

    return rest->available;
}

int cal_consistency(User* user, Rest* rest, int mode)
{
    int score = 30;

    if (mode == 0)
    {
        score = (int)(rest->rating * 12) + rest->speed * 6;

        if (rest->distance <= 100) score += 25;
        else if (rest->distance <= 300) score += 18;
        else if (rest->distance <= 600) score += 10;
        else if (rest->distance <= 1000) score += 3;
        else score -= 8;

        rest->score = score;
        return score;
    }

    if (strcmp(user->want_genre, rest->genre) == 0)
        score += 25;
    else if (strcmp(user->before_eat, rest->genre) == 0)
        score -= 10;

    if (strcmp(user->mood, "데이트") == 0)
    {
        if (strcmp(rest->genre, "양식") == 0) score += 24;
        else if (strcmp(rest->genre, "일식") == 0) score += 14;
        else if (strcmp(rest->genre, "아시안") == 0) score += 10;

        if (rest->price >= 3) score += 12;
        else if (rest->price == 2) score += 5;

        if (rest->rating >= 4.3) score += 8;
        if (user->left_time >= 90) score += 15;
        else if (user->left_time >= 60) score += 8;
        if (user->headcount == 2) score += 8;
    }
    else if (strcmp(user->mood, "혼밥") == 0)
    {
        if (user->headcount == 1) score += 12;
        if (rest->price <= 2) score += 12;
        if (rest->speed >= 4) score += 14;
        if (rest->distance <= 300) score += 12;
        else if (rest->distance <= 600) score += 6;
        if (strcmp(rest->genre, "분식") == 0 || strcmp(rest->genre, "한식") == 0 || strcmp(rest->genre, "일식") == 0) score += 8;
        if (rest->price >= 4) score -= 8;
    }
    else if (strcmp(user->mood, "술") == 0)
    {
        if (contains_text(rest->name, "호프") || contains_text(rest->name, "포차") ||
            contains_text(rest->name, "이자카야") || contains_text(rest->name, "맥주") ||
            contains_text(rest->name, "술") || contains_text(rest->name, "비어"))
            score += 25;

        if (strcmp(rest->genre, "양식") == 0 || strcmp(rest->genre, "일식") == 0) score += 10;
        else if (strcmp(rest->genre, "한식") == 0 || strcmp(rest->genre, "기타") == 0) score += 8;

        if (rest->price >= 3) score += 12;
        if (user->left_time >= 90) score += 12;
        else if (user->left_time >= 60) score += 5;
        if (user->headcount >= 2) score += 8;
    }

    if (rest->rating >= 4.5) score += 15;
    else if (rest->rating >= 4.0) score += 10;
    else if (rest->rating >= 3.5) score += 5;
    else if (rest->rating < 2.0) score -= 8;

    if (user->poor <= 2)
    {
        if (rest->price == 1) score += 18;
        else if (rest->price == 2) score += 8;
        else if (rest->price == 3) score -= 8;
        else score -= 15;
    }
    else if (user->poor == 3)
    {
        if (rest->price == 1) score += 12;
        else if (rest->price == 2) score += 10;
        else if (rest->price == 3) score += 3;
        else score -= 5;
    }
    else
    {
        if (rest->price >= 3) score += 8;
        else score += 4;
    }

    if (user->left_time <= 40)
    {
        if (rest->speed >= 5) score += 25;
        else if (rest->speed == 4) score += 18;
        else if (rest->speed == 3) score += 5;
        else score -= 20;
    }
    else if (user->left_time <= 60)
    {
        if (rest->speed >= 4) score += 18;
        else if (rest->speed == 3) score += 10;
        else if (rest->speed == 2) score += 2;
        else score -= 10;
    }
    else
    {
        if (rest->speed >= 3) score += 8;
        else score += 3;
    }

    if (user->hungriness >= 4)
    {
        if (rest->distance <= 100) score += 30;
        else if (rest->distance <= 300) score += 25;
        else if (rest->distance <= 600) score += 15;
        else if (rest->distance <= 1000) score += 5;
        else score -= 15;
    }
    else if (user->hungriness == 3)
    {
        if (rest->distance <= 100) score += 20;
        else if (rest->distance <= 300) score += 15;
        else if (rest->distance <= 600) score += 10;
        else if (rest->distance <= 1000) score += 5;
        else score -= 5;
    }
    else
    {
        if (rest->distance <= 600) score += 8;
        else if (rest->distance <= 1000) score += 3;
    }

    rest->score = score;
    return score;
}

static int read_restaurant(FILE* fp, Rest* rest)
{
    char line[4096];
    char fields[MAX_FIELDS][MAX_FIELD];
    int count;

    if (fgets(line, sizeof(line), fp) == NULL)
        return 0;

    count = split_csv(line, fields, MAX_FIELDS);
    if (count < 12)
        return 0;

    memset(rest, 0, sizeof(Rest));

    safe_copy(rest->id, fields[0], sizeof(rest->id));
    safe_copy(rest->name, fields[1], sizeof(rest->name));
    safe_copy(rest->genre, fields[2], sizeof(rest->genre));
    safe_copy(rest->location, fields[3], sizeof(rest->location));
    rest->open_time = to_int_default(fields[4], 0);
    rest->close_time = to_int_default(fields[5], 2359);
    rest->rating = to_float_default(fields[6], 3.0f);
    rest->price = to_int_default(fields[7], 2);
    rest->speed = to_int_default(fields[8], 3);
    rest->break_start = to_int_default(fields[9], 0);
    rest->break_end = to_int_default(fields[10], 0);
    rest->distance = to_float_default(fields[11], 9999.0f);

    if (count > 12) safe_copy(rest->kakao_url, fields[12], sizeof(rest->kakao_url));
    if (count > 13) rest->lat = to_float_default(fields[13], 0.0f);
    if (count > 14) rest->lon = to_float_default(fields[14], 0.0f);

    if (rest->lat != 0.0f && rest->lon != 0.0f)
        rest->has_location = 1;
    else
        rest->has_location = 0;

    if (rest->name[0] == '\0')
        return 0;

    return 1;
}

void make_list(Node* head, User* user, int now_time, int mode)
{
    FILE* fp;
    char header[4096];
    char filename[64] = "Restaurant_runtime.csv";

    fp = fopen(filename, "r");
    if (fp == NULL)
    {
        safe_copy(filename, "Restaurant_core.csv", sizeof(filename));
        fp = fopen(filename, "r");
    }

    if (fp == NULL)
    {
        printf("식당 데이터 파일을 열 수 없습니다....\n");
        return;
    }

    fgets(header, sizeof(header), fp);

    while (1)
    {
        Rest rest;
        Node* node;

        if (read_restaurant(fp, &rest) == 0)
            break;

        cal_availability(&rest, now_time);

        if (!rest.available)
            continue;

        cal_consistency(user, &rest, mode);

        node = (Node*)malloc(sizeof(Node));
        if (node == NULL)
        {
            printf("메모리 할당에 실패했습니다....\n");
            break;
        }

        node->rest = rest;
        node->next = NULL;
        insert_node_sorted(head, node);
    }

    fclose(fp);
}

void insert_node_sorted(Node* head, Node* node)
{
    Node* current;

    if (node == NULL)
        return;

    current = head;

    while (current->next != NULL && current->next->rest.score >= node->rest.score)
        current = current->next;

    node->next = current->next;
    current->next = node;
}

Node* pop_node(Node* head, int index)
{
    Node* current = head;
    Node* target;
    int count = 0;

    if (index < 0)
        return NULL;

    while (current->next != NULL && count < index)
    {
        current = current->next;
        count++;
    }

    if (current->next == NULL)
        return NULL;

    target = current->next;
    current->next = target->next;
    target->next = NULL;

    return target;
}

Node* get_node(Node* head, int index)
{
    Node* current = head->next;
    int count = 0;

    if (index < 0)
        return NULL;

    while (current != NULL && count < index)
    {
        current = current->next;
        count++;
    }

    return current;
}

void append_node(Node* head, Node* node)
{
    Node* current = head;

    if (node == NULL)
        return;

    while (current->next != NULL)
        current = current->next;

    current->next = node;
    node->next = NULL;
}

void show_recommend_list(Node* recommend_head, int show_count)
{
    Node* current = recommend_head->next;
    int i = 1;

    printf("\n========== 추천 식당 리스트 ==========\n");

    if (current == NULL)
    {
        printf("현재 영업 중인 식당이 없습니다....\n");
        return;
    }

    while (current != NULL && i <= show_count)
    {
        printf("%2d. %s\n", i, current->rest.name);
        printf("    종류 : %s / 평점 : %.1f / 도보거리 : %.0fm\n",
            current->rest.genre,
            current->rest.rating,
            current->rest.distance
        );
        i++;
        current = current->next;
    }

    printf("======================================\n");
}

void show_sub_list(Node* head, char* title)
{
    Node* current = head->next;
    int i = 1;

    printf("\n--- %s ---\n", title);

    if (current == NULL)
    {
        printf("비어 있습니다....\n");
        return;
    }

    while (current != NULL)
    {
        printf("%2d. %s / %s / 도보거리 %.0fm\n",
            i,
            current->rest.name,
            current->rest.genre,
            current->rest.distance
        );
        i++;
        current = current->next;
    }
}

void save_list_to_file(Node* head, char* filename)
{
    FILE* fp;
    Node* current;

    fp = fopen(filename, "w");
    if (fp == NULL)
    {
        printf("%s save error....\n", filename);
        return;
    }

    fprintf(fp, "Name,Genre,Rating,Distance,Score,Location,lat,lon,Kakao_URL\n");

    current = head->next;
    while (current != NULL)
    {
        write_csv_text(fp, current->rest.name); fprintf(fp, ",");
        write_csv_text(fp, current->rest.genre); fprintf(fp, ",");
        fprintf(fp, "%.1f,%.0f,%d,",
            current->rest.rating,
            current->rest.distance,
            current->rest.score
        );
        write_csv_text(fp, current->rest.location); fprintf(fp, ",");
        fprintf(fp, "%.7f,%.7f,", current->rest.lat, current->rest.lon);
        write_csv_text(fp, current->rest.kakao_url); fprintf(fp, "\n");
        current = current->next;
    }

    fclose(fp);
}

void save_top_n_to_file(Node* head, char* filename, int n)
{
    FILE* fp;
    Node* current;
    int count = 0;

    fp = fopen(filename, "w");
    if (fp == NULL)
    {
        printf("%s save error....\n", filename);
        return;
    }

    fprintf(fp, "Name,Genre,Rating,Distance,Score,Location,lat,lon,Kakao_URL\n");

    current = head->next;
    while (current != NULL && count < n)
    {
        write_csv_text(fp, current->rest.name); fprintf(fp, ",");
        write_csv_text(fp, current->rest.genre); fprintf(fp, ",");
        fprintf(fp, "%.1f,%.0f,%d,",
            current->rest.rating,
            current->rest.distance,
            current->rest.score
        );
        write_csv_text(fp, current->rest.location); fprintf(fp, ",");
        fprintf(fp, "%.7f,%.7f,", current->rest.lat, current->rest.lon);
        write_csv_text(fp, current->rest.kakao_url); fprintf(fp, "\n");
        count++;
        current = current->next;
    }

    fclose(fp);
}

void save_one_to_file(Node* node, char* filename)
{
    FILE* fp;

    if (node == NULL)
        return;

    fp = fopen(filename, "w");
    if (fp == NULL)
        return;

    fprintf(fp, "Name,Genre,Rating,Distance,Score,Location,lat,lon,Kakao_URL\n");
    write_csv_text(fp, node->rest.name); fprintf(fp, ",");
    write_csv_text(fp, node->rest.genre); fprintf(fp, ",");
    fprintf(fp, "%.1f,%.0f,%d,", node->rest.rating, node->rest.distance, node->rest.score);
    write_csv_text(fp, node->rest.location); fprintf(fp, ",");
    fprintf(fp, "%.7f,%.7f,", node->rest.lat, node->rest.lon);
    write_csv_text(fp, node->rest.kakao_url); fprintf(fp, "\n");

    fclose(fp);
}

void print_command_help(void)
{
    printf("\n[명령어]\n");
    printf("n              : 5개 더 보기\n");
    printf("d 번호         : 추천 목록에서 영구 삭제, 다시 복구 불가\n");
    printf("h 번호         : 추천 목록에서 보류\n");
    printf("r              : 보류 목록에서 복구\n");
    printf("l              : 삭제/보류 목록 확인\n");
    printf("m              : 현재 위치와 상위 5개 식당을 지도로 보기\n");
    printf("g 번호         : 해당 식당까지 가는 길 보기\n");
    printf("b              : main 화면으로 돌아가기\n");
    printf("q              : 종료\n");
}

int run_terminal(Node* recommend_head)
{
    Node deleted_head;
    Node hold_head;
    int show_count = SHOW_STEP;
    char command[128];

    deleted_head.next = NULL;
    hold_head.next = NULL;

    save_list_to_file(recommend_head, "recommend_list.txt");
    save_list_to_file(&deleted_head, "deleted_list.txt");
    save_list_to_file(&hold_head, "hold_list.txt");

    show_recommend_list(recommend_head, show_count);
    print_command_help();

    while (1)
    {
        char op;
        int index = 0;

        printf("\n명령어 >> ");
        if (fgets(command, sizeof(command), stdin) == NULL)
            break;

        if (sscanf(command, " %c %d", &op, &index) < 1)
            continue;

        if (op == 'q' || op == 'Q')
        {
            printf("프로그램을 종료합니다....\n");
            free_list(deleted_head.next);
            free_list(hold_head.next);
            return 0;
        }
        else if (op == 'b' || op == 'B')
        {
            printf("main 화면으로 돌아갑니다....\n");
            free_list(deleted_head.next);
            free_list(hold_head.next);
            return 1;
        }
        else if (op == 'n' || op == 'N')
        {
            show_count += SHOW_STEP;
            show_recommend_list(recommend_head, show_count);
        }
        else if (op == 'd' || op == 'D')
        {
            Node* target = pop_node(recommend_head, index - 1);
            if (target == NULL)
                printf("그 번호는 없습니다....\n");
            else
            {
                printf("영구 삭제: %s\n", target->rest.name);
                append_node(&deleted_head, target);
            }
            show_recommend_list(recommend_head, show_count);
        }
        else if (op == 'h' || op == 'H')
        {
            Node* target = pop_node(recommend_head, index - 1);
            if (target == NULL)
                printf("그 번호는 없습니다....\n");
            else
            {
                printf("보류: %s\n", target->rest.name);
                append_node(&hold_head, target);
            }
            show_recommend_list(recommend_head, show_count);
        }
        else if (op == 'l' || op == 'L')
        {
            show_sub_list(&deleted_head, "영구 삭제 목록");
            show_sub_list(&hold_head, "보류 목록");
        }
        else if (op == 'r' || op == 'R')
        {
            int restore_index;
            Node* target = NULL;

            show_sub_list(&hold_head, "보류 목록");
            printf("복구할 보류 번호 >> ");
            if (scanf("%d", &restore_index) != 1)
                restore_index = -1;
            while (getchar() != '\n')
                ;

            target = pop_node(&hold_head, restore_index - 1);

            if (target == NULL)
                printf("복구할 수 없습니다....\n");
            else
            {
                printf("복구: %s\n", target->rest.name);
                insert_node_sorted(recommend_head, target);
            }

            show_recommend_list(recommend_head, show_count);
        }
        else if (op == 'm' || op == 'M')
        {
            printf("지도를 여는 중입니다....\n");
            save_top_n_to_file(recommend_head, "top5_map_input.csv", 5);
            run_python_script("show_top5_map.py", "top5_map_input.csv", "user_location.txt");
        }
        else if (op == 'g' || op == 'G')
        {
            Node* target = get_node(recommend_head, index - 1);
            if (target == NULL)
                printf("그 번호는 없습니다....\n");
            else
            {
                printf("가는 길을 여는 중입니다: %s\n", target->rest.name);
                save_one_to_file(target, "route_input.csv");
                run_python_script("show_route.py", "route_input.csv", "user_location.txt");
            }
        }
        else
        {
            print_command_help();
        }

        save_list_to_file(recommend_head, "recommend_list.txt");
        save_list_to_file(&deleted_head, "deleted_list.txt");
        save_list_to_file(&hold_head, "hold_list.txt");
    }

    free_list(deleted_head.next);
    free_list(hold_head.next);
    return 0;
}

void free_list(Node* head)
{
    Node* current = head;
    Node* temp;

    while (current != NULL)
    {
        temp = current;
        current = current->next;
        free(temp);
    }
}

int main(void)
{
    init_console();

    while (1)
    {
        User user;
        Node recommend_head;
        int mode;
        int now_time;
        int go_back;

        user_init(&user);
        recommend_head.next = NULL;

        mode = open_main_ui();
        if (mode < 0)
            mode = ask_mode_terminal();

        if (mode == 9)
        {
            printf("프로그램을 종료합니다....\n");
            break;
        }

        if (mode == 1)
            read_user_settings(&user);
        else if (mode == 2)
            get_user_information(&user);

        prepare_location_and_distance();
        cal_time(&now_time);

        print_current_time(now_time);
        printf("추천 식당을 불러옵니다....\n");
        printf("영업 중인 식당만 골라냈습니다....\n");

        make_list(&recommend_head, &user, now_time, mode);
        go_back = run_terminal(&recommend_head);

        free_list(recommend_head.next);

        if (!go_back)
            break;
    }

    return 0;
}
