test: test_audio.wav wav_splitter.py
	./wav_splitter.py -d 60 test_audio.wav -o foo

test_audio.wav:
	sox -n $@ synth 300 sine 440

clean:
	rm -f test_audio.wav
	rm -fr foo

.PHONY: test
.PHONY: clean

