JAVAC = javac
JAVA = java
SRC = QuestionBank.java
MAIN_CLASS = QuestionBank

all: $(MAIN_CLASS)

$(MAIN_CLASS): $(SRC)
	$(JAVAC) $(SRC)

run: $(MAIN_CLASS)
	$(JAVA) $(MAIN_CLASS)

clean:
	rm -f *.class
