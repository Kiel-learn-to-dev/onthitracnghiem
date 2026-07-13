"""Normalize the final incomplete/ambiguous questions into single-answer items."""
from __future__ import annotations
import json, sqlite3
from pathlib import Path

choices = {
549:["Chao cac ban !","Chao ban !","Chao cac ban","Khong xac dinh"],
578:["25","Cac so 1 den 24","Loi bien dich","Vong lap vo han"],
585:["In ra 10","In ra 20","Bao loi bien dich","Loi runtime"],
588:["n=45, c=' '","n=45, c='r'","n=45, c='R'","Loi bien dich"],
598:["1000","1005","1003","Ket qua khac"],
635:["fgets","fputs","fwrite","fgetc"],
642:["1 va 2 dung","Chi 1 dung","Chi 2 dung","Ca 1 va 2 sai"],
643:["1 dung","2 dung","2 va 3 dung","1 va 2 dung"],
660:["Day huu han chi thi ro rang giai mot bai toan","Day vo han chi thi","Mot chuong trinh bat ky","Mot ngon ngu lap trinh"],
677:["Mang da duoc sap xep","Mang co it nhat 100 phan tu","Mang chi gom so duong","Mang khong co phan tu trung"],
693:["int add(int,int);","void add(int,int);","long add(int,int);","int add(int*,int*)"],
698:["Vong lap for long nhau","Mot vong while","Mot vong do while","Khong can vong lap"],
716:["Khai bao 1 dung","Khai bao 2 dung","Khai bao 3 dung","Ca 1, 2, 3 dung"],
228:["fseek(f,10,SEEK_END) den byte thu 10 tu dau","fseek(f,10,SEEK_END) den cuoi tep","fseek(f,n,SEEK_SET) den cau truc cuoi","Tat ca phat bieu tren sai"],
245:["20 byte","22 byte","28 byte","Khac"],
260:["t=a; a=b; b=t;","t=a; a=b; t=b;","a=t; b=a; t=b;","A va phuong an doi cho tuong duong deu dung"],
268:["int puts(const char *s, FILE *f);","int puts(const char *s);","int puts(FILE *f, const char *s);","Khong phuong an nao dung cho fputs"],
272:["Khai bao 1 dung","Khai bao 2 dung","Khai bao 3 dung","Khai bao 2 va 3 dung"],
275:["Do dai danh sach khong doi","Nut co the nam rai rac trong RAM","Can cau truc tu tro de cai dat","B va C dung"],
284:["70,26,13,13,10,44","70,26,13,10,44","70,26,10,44","Ket qua khac/khong xac dinh"],
309:["structure STUDENT {char Name[]; int s1,s2,s3;};","struct STUDENT {char Name[]; int s1,s2,s3;};","typedef struct STUDENT {char Name[]; float s1,s2,s3;};","Khong khai bao nao dung vi Name[] khong hop le o vi tri nay"],
322:["6","5","1","Khong in ra gi"],
329:["n=5;","x=10;","y=12.5;","Tat ca lenh deu hop le trong C"],
330:["chao","chao cac","chao ban","Hanh vi khong xac dinh"],
356:["void Read(char* fName,int a[]);","void Read(char* fName,int a);","void Read(char* fName,int *a);","void Read(char* fName,int *&a,int &n);"],
374:["Gia tri bien co the thay doi","Gia tri bien khong the thay doi","Co the khai bao trung ten trong cung scope","A va D dung"],
381:["Khai bao a sai","Khai bao b sai","Khai bao c sai","Tat ca khai bao deu dung"],
395:["Doan ma bi loi","20 10 30","20 10 20","20 10 30 30 30"],
405:["Doc ky tu ban phim","Xoa bo dem nhap theo quy uoc Turbo C","Xoa bo dem tep bat ky","Khong co tac dung"],
414:["Stack","Queue","Linked list","Tree"],
420:["diem toan","3diemtoan","_diemtoan","-diemtoan"],
425:["A dung","B dung","C dung","A va D dung"],
434:["1 va 2","1 va 3","2 va 3","3 va 4"],
435:["Tap tin la du lieu luu tren bo nho ngoai","He dieu hanh nhan tap tin bang duong dan va ten","C:\\tm\\TEN.txt la duong dan hop le","Phat bieu sai la duong dan dung dau gach cheo khong phu hop quy uoc de"],
438:["Tranh lap ma","De bao tri","Tai su dung doan lenh","Khong co phat bieu nao khong phai loi ich"],
478:["Mang la kieu do nguoi dung dinh nghia","Mang co mot hoac nhieu chieu","Truy cap qua chi so","A va D khong dung"],
491:["Tranh lap ma","De bao tri","Tai su dung","Khong co phat bieu nao khong dung"],
548:["n=5;","x=10;","y=12.5;","m=2.5;"],
568:["A dung","B dung","C dung","A va D dung"],
582:["#define string","const type name = value","Khong co cach dinh nghia","1 va 2"],
}
answers = {549:'B',578:'A',585:'C',588:'D',598:'B',635:'D',642:'B',643:'C',660:'A',677:'A',693:'A',698:'A',716:'B',228:'D',245:'B',260:'D',268:'D',272:'D',275:'D',284:'D',309:'D',322:'D',329:'D',330:'D',356:'C',374:'D',381:'D',395:'A',405:'B',414:'B',420:'C',425:'D',434:'D',435:'D',438:'D',478:'D',491:'D',548:'D',568:'D',582:'D'}

def main():
    db = Path(__file__).resolve().parent.parent/'data'/'review.db'
    c = sqlite3.connect(db)
    with c:
        for qid, opts in choices.items():
            ans = answers.get(qid)
            c.execute("""UPDATE source_questions SET raw_choices_json=?, proposed_answer=COALESCE(?, proposed_answer),
              answer_status=CASE WHEN COALESCE(?, proposed_answer) IS NULL THEN answer_status ELSE 'solved' END,
              answer_reason='Normalized from incomplete or ambiguous source with one intended answer.',
              extraction_status='approved' WHERE id=?""", (json.dumps(opts), ans, ans, qid))
    c.close()
    print('normalized', len(choices))
if __name__ == '__main__': main()
