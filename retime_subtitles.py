from datetime import datetime
from abc import ABC, abstractmethod


class Retimer:
    def __init__(self):
        self.inputPath = ''
        self.numberOfLines = 0
        self.outputPath = ''

    def setInputPath(self, inputPath: str):
        self.inputPath = inputPath
        with open(self.inputPath, 'r') as f:
            self.numberOfLines = len(f.readlines())

    def setOutputPath(self, outputPath):
        self.outputPath = outputPath
        if self.outputPath[-1] != '/':
            self.outputPath += '/'
    
    def read(self, delay=0, forward=True):
        if not self.inputPath:
            raise ValueError("No input path specified. Use Retimer.setInputPath() method")
        if not self.outputPath:
            raise ValueError("No output path specified. Use Retimer.setOutputPath() method")
        
        self.text = open(self.inputPath, "r")
        self.newFile = open(self.outputPath + 'retimed_' + (str(datetime.now())[:19] + '.srt').replace(':', '-').replace(' ', '-'), 'w')
        tf = TimeFormatter()
        tf.formatDelay(delay, forward)
        for i in range(self.numberOfLines):
            self.line = self.text.readline().strip()
            if '-->' in self.line:
                self.line = tf.formatDictionary({ 0: self.line[:12], 1: self.line[17:] })
                self.newFile.write(f"{self.line[0]} --> {self.line[1]}\n")
            else:
                self.newFile.write(self.line + '\n')
        del tf
        self.newFile.close()


class ItemFormattingStrategy(ABC):
    @abstractmethod
    def check(self, first: int, second: int) -> bool:
        pass

    @abstractmethod
    def progress(self) -> int:
        pass

    @abstractmethod
    def setSegment(self, first: int, second: int) -> str:
        pass

    @abstractmethod
    def setHour(self, hour: int, segment: int) -> str:
        pass

    @abstractmethod
    def finalFormat(self, hour: str, minute: str, second: str, miliseconds: str) -> str:
        pass


class ForwardItemFormattingStrategy(ItemFormattingStrategy):
    def check(self, first: int, second: int) -> bool:
        return first + second >= 60
    
    def progress(self) -> int:
        return 1
    
    def setSegment(self, first: int, second: int) -> str:
        if len(str((first + second) % 60)) == 1:
            return '0' + str((first + second) % 60)
        return str((first + second) % 60)
    
    def setHour(self, hour: int, segment: int) -> str:
        if len(str(hour + segment)) == 1:
            return '0' + str(hour + segment)
        return str(hour + segment)
    
    def finalFormat(self, hour: str, minute: str, second: str, miliseconds: str) -> str:
        return f'{hour}:{minute}:{second},{miliseconds}'


class BackwardItemFormattingStrategy(ItemFormattingStrategy):
    def __init__(self):
        self.isNegative = False

    def check(self, first: int, second: int) -> bool:
        return first - second < 0
    
    def progress(self) -> int:
        return -1
    
    def setSegment(self, first: int, second: int) -> str:
        if len(str((first - second)%60)) == 1:
            return '0' + str((first - second)%60)
        return str((first - second)%60)
    
    def setHour(self, hour: int, segment: int) -> str:
        self.isNegative = False
        if hour - segment < 0:
            self.isNegative = True
        if len(str(hour - segment)) == 1:
            return '0' + str(hour - segment)
        elif len(str(hour - segment)) == 2 and not str(hour - segment)[0].isnumeric():
            return '-0' + str(hour - segment)[-1]
        return str(hour - segment)
    
    def finalFormat(self, hour: str, minute: str, second: str, miliseconds: str) -> str:
        if self.isNegative:
            miliseconds = str(1000 - int(miliseconds))
            while len(miliseconds) < 3:
                miliseconds = '0' + miliseconds
            minute = str(59-(int(minute)))
            if len(minute) == 1:
                minute = '0' + minute
            second = str(60-(int(second)))
            if len(second) == 1:
                second = '0' + second
            hour = str(1 + int(hour))
            if len(hour) == 1:
                hour = '-0' + hour
            elif len(hour) == 2 and not hour[0].isnumeric():
                hour = '-0' + hour[-1]
            return f'{hour}:{minute}:{second},{miliseconds}'
        return f'{hour}:{minute}:{second},{miliseconds}'


class TimeFormatter:
    def __init__(self):
        self.times = {}
        self.hour = '00'
        self.minute = '00'
        self.second = '00'
        self.formattedDelay = ''
        self.forward = True
        self.formattingStrategy = ForwardItemFormattingStrategy()

    def setFormattingStrategy(self, strategy: ItemFormattingStrategy):
        self.formattingStrategy = strategy

    def formatDelay(self, delay: int, forward: bool=True) -> None:
        self.delay = delay
        if not forward:
            self.setFormattingStrategy(BackwardItemFormattingStrategy())

        if self.delay >= 3600:
            self.hour = str(int(self.delay/3600))
            if len(self.hour) == 1:
                self.hour = '0'+self.hour
            self.delay = self.delay%3600

        if self.delay >= 60:
            self.minute = str(int(self.delay/60))
            if len(self.minute) == 1:
                self.minute = '0'+self.minute
            self.delay = self.delay%60
        self.second = str(self.delay)

        if len(self.second) == 1:
            self.second = '0'+self.second

        self.formattedDelay = f'{self.hour}:{self.minute}:{self.second},000'

    def formatDictionary(self, times: dict[int, str]) -> dict[int, str]:
        self.times = times.copy()
        for item in range(2):
            self.formatItem(self.times[item], item)
        return self.times

    def formatItem(self, item: str, dictKey: int):
        self.hour, self.minute, self.second = int(item[:2]), int(item[3:5]), int(item[6:8])
        
        if self.formattingStrategy.check(self.second, int(self.formattedDelay[6:8])):
            self.minute += self.formattingStrategy.progress()
        self.second = self.formattingStrategy.setSegment(self.second, int(self.formattedDelay[6:8]))

        if self.formattingStrategy.check(self.minute, int(self.formattedDelay[3:5])):
            self.hour += self.formattingStrategy.progress()
        self.minute = self.formattingStrategy.setSegment(self.minute, int(self.formattedDelay[3:5]))

        self.hour = self.formattingStrategy.setHour(int(self.hour), int(self.formattedDelay[:2]))

        self.item = self.formattingStrategy.finalFormat(self.hour, self.minute, self.second, item[9:])
        self.times[dictKey] = self.item
        


def main():
    r = Retimer()
    r.setInputPath('path/to/file.srt')
    r.setOutputPath('path/to/output/folder/')
    r.read(120, False)


if __name__ == '__main__':
    main()
