JAVAC = javac
JAVA_FLAGS = -cp
JAVA = java
JAVA_SOURCE = QuestionBank.java
JAVA_CLASS = QuestionBank

all: compile

compile:
	$(JAVAC) $(JAVA_FLAGS) . $(JAVA_SOURCE)

run-python:
	$(JAVA) $(JAVA_FLAGS) . $(JAVA_CLASS) python

run-java:
	$(JAVA) $(JAVA_FLAGS) . $(JAVA_CLASS) java

clean:
	rm -f *.class
